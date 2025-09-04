"""
Management command to validate collections using galaxy-importer.
"""
from django.core.management.base import BaseCommand

from galaxy_ng.app.content.collections import CollectionManager
from galaxy_ng.app.content.repositories import ContentRepository
from galaxy_ng.app.content.validation import validate_collection_artifact, CollectionValidationError
from galaxy_ng.app.tasks_pg.dispatcher import dispatcher
from galaxy_ng.app.tasks_pg.tasks import validate_existing_collection, bulk_validate_collections


class Command(BaseCommand):
    help = 'Validate collections using galaxy-importer'

    def add_arguments(self, parser):
        parser.add_argument(
            '--namespace',
            type=str,
            help='Validate collections in specific namespace'
        )
        parser.add_argument(
            '--collection',
            type=str,
            help='Validate specific collection (requires --namespace)'
        )
        parser.add_argument(
            '--version',
            type=str,
            help='Validate specific version (requires --namespace and --collection)'
        )
        parser.add_argument(
            '--repository',
            type=str,
            help='Validate collections in specific repository (staging, approved, etc.)'
        )
        parser.add_argument(
            '--async',
            action='store_true',
            help='Run validation as background tasks'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-validate collections even if already validated'
        )
        parser.add_argument(
            '--quick',
            action='store_true',
            help='Only run quick validation (basic format checks)'
        )

    def handle(self, *args, **options):
        namespace = options.get('namespace')
        collection = options.get('collection') 
        version = options.get('version')
        repository = options.get('repository')
        run_async = options.get('async')
        force = options.get('force')
        quick = options.get('quick')

        collection_manager = CollectionManager()
        repository_manager = ContentRepository()

        if namespace and collection and version:
            # Validate specific collection version
            self._validate_single_collection(
                namespace, collection, version, run_async, force, quick
            )
            
        elif namespace and collection:
            # Validate all versions of a collection
            versions = collection_manager.list_collection_versions(namespace, collection)
            if not versions:
                self.stdout.write(
                    self.style.ERROR(f'No versions found for {namespace}.{collection}')
                )
                return
            
            self.stdout.write(
                f'Found {len(versions)} versions of {namespace}.{collection}'
            )
            
            for version in versions:
                self._validate_single_collection(
                    namespace, collection, version, run_async, force, quick
                )
                
        elif namespace:
            # Validate all collections in namespace
            collections = collection_manager.list_namespace_collections(namespace)
            if not collections:
                self.stdout.write(
                    self.style.ERROR(f'No collections found in namespace {namespace}')
                )
                return
            
            self.stdout.write(f'Found {len(collections)} collections in {namespace}')
            
            for collection_name in collections:
                versions = collection_manager.list_collection_versions(namespace, collection_name)
                for version in versions:
                    self._validate_single_collection(
                        namespace, collection_name, version, run_async, force, quick
                    )
                    
        elif repository:
            # Validate all collections in repository
            if run_async:
                task = dispatcher.dispatch(
                    bulk_validate_collections,
                    kwargs={'repository': repository}
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Started bulk validation task for repository {repository}: {task.pulp_id}'
                    )
                )
            else:
                collections = repository_manager.list_repository_collections(repository)
                self.stdout.write(f'Found {len(collections)} collections in {repository}')
                
                for collection_info in collections:
                    self._validate_single_collection(
                        collection_info['namespace'],
                        collection_info['name'],
                        collection_info['version'],
                        False, force, quick
                    )
        else:
            # Validate all collections
            if run_async:
                task = dispatcher.dispatch(bulk_validate_collections)
                self.stdout.write(
                    self.style.SUCCESS(f'Started bulk validation task: {task.pulp_id}')
                )
            else:
                self.stdout.write('Validating all collections...')
                namespaces = collection_manager.list_namespaces()
                
                total_collections = 0
                for namespace in namespaces:
                    collections = collection_manager.list_namespace_collections(namespace)
                    for collection_name in collections:
                        versions = collection_manager.list_collection_versions(namespace, collection_name)
                        total_collections += len(versions)
                        
                        for version in versions:
                            self._validate_single_collection(
                                namespace, collection_name, version, False, force, quick
                            )
                
                self.stdout.write(
                    self.style.SUCCESS(f'Completed validation of {total_collections} collections')
                )

    def _validate_single_collection(self, namespace: str, collection: str, version: str,
                                   run_async: bool, force: bool, quick: bool):
        """Validate a single collection version."""
        collection_manager = CollectionManager()
        
        if not collection_manager.collection_exists(namespace, collection, version):
            self.stdout.write(
                self.style.ERROR(f'Collection not found: {namespace}.{collection}:{version}')
            )
            return
        
        # Check if already validated (unless force is specified)
        if not force:
            try:
                metadata = collection_manager.get_collection_metadata(namespace, collection, version)
                if metadata.get('validation_result') is not None:
                    validation_result = metadata['validation_result']
                    if validation_result.get('valid'):
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✓ {namespace}.{collection}:{version} - Already validated'
                            )
                        )
                        return
                    else:
                        self.stdout.write(
                            self.style.ERROR(
                                f'✗ {namespace}.{collection}:{version} - Previously failed validation'
                            )
                        )
                        return
            except Exception:
                pass  # Continue with validation if metadata can't be read
        
        if run_async:
            # Dispatch async task
            task = dispatcher.dispatch(
                validate_existing_collection,
                args=(namespace, collection, version)
            )
            self.stdout.write(
                f'⏳ {namespace}.{collection}:{version} - Validation task: {task.pulp_id}'
            )
        else:
            # Run validation synchronously
            try:
                artifact_path = collection_manager.get_collection_artifact(namespace, collection, version)
                validation_result = validate_collection_artifact(artifact_path, quick_only=quick)
                
                if validation_result['valid']:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ {namespace}.{collection}:{version} - Valid'
                        )
                    )
                    if validation_result.get('warnings'):
                        for warning in validation_result['warnings']:
                            self.stdout.write(
                                self.style.WARNING(f'  Warning: {warning}')
                            )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f'✗ {namespace}.{collection}:{version} - Invalid'
                        )
                    )
                    for error in validation_result.get('errors', []):
                        self.stdout.write(
                            self.style.ERROR(f'  Error: {error}')
                        )
                        
            except CollectionValidationError as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ {namespace}.{collection}:{version} - {str(e)}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ {namespace}.{collection}:{version} - Error: {str(e)}')
                )