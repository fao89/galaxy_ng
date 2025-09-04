#!/usr/bin/env python3
"""
Simple HTTP server for serving filesystem content.
"""
import argparse
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json
import mimetypes


class ContentHandler(SimpleHTTPRequestHandler):
    """Custom handler for serving collection content."""
    
    def __init__(self, *args, content_root="/content", **kwargs):
        self.content_root = Path(content_root)
        super().__init__(*args, **kwargs)
    
    def translate_path(self, path):
        """Translate URL path to filesystem path."""
        # Remove leading slash and any query parameters
        path = path.split('?')[0].split('#')[0].lstrip('/')
        
        if path.startswith('health/'):
            return None  # Handle in do_GET
        
        # Map content URLs to filesystem paths
        if path.startswith('collections/'):
            # Collection artifact download
            # Format: collections/{namespace}/{name}/versions/{version}/download/
            parts = path.split('/')
            if len(parts) >= 6 and parts[4] == 'versions' and parts[6] == 'download':
                namespace, name, version = parts[1], parts[2], parts[5]
                artifact_path = (
                    self.content_root / 'collections' / namespace / name / 
                    'versions' / version / f"{namespace}-{name}-{version}.tar.gz"
                )
                return str(artifact_path)
        
        elif path.startswith('namespaces/'):
            # Namespace avatar
            # Format: namespaces/{namespace}/avatar/
            parts = path.split('/')
            if len(parts) >= 3 and parts[2] == 'avatar':
                namespace = parts[1]
                # Try common avatar file extensions
                for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg']:
                    avatar_path = self.content_root / 'collections' / namespace / f'avatar{ext}'
                    if avatar_path.exists():
                        return str(avatar_path)
        
        # Default: serve from content root
        full_path = self.content_root / path
        return str(full_path)
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path.startswith('/health/'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {
                'status': 'healthy',
                'content_root': str(self.content_root),
                'service': 'galaxy-ng-content-server'
            }
            self.wfile.write(json.dumps(response).encode())
            return
        
        file_path = self.translate_path(self.path)
        
        if file_path is None:
            self.send_error(404, "File not found")
            return
        
        path_obj = Path(file_path)
        
        if not path_obj.exists():
            self.send_error(404, "File not found")
            return
        
        if not path_obj.is_file():
            self.send_error(403, "Not a file")
            return
        
        # Send file
        try:
            with open(file_path, 'rb') as f:
                self.send_response(200)
                
                # Determine content type
                content_type, _ = mimetypes.guess_type(file_path)
                if content_type is None:
                    if file_path.endswith('.tar.gz'):
                        content_type = 'application/gzip'
                    else:
                        content_type = 'application/octet-stream'
                
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(path_obj.stat().st_size))
                
                # For downloads, suggest filename
                if self.path.endswith('/download/') or file_path.endswith('.tar.gz'):
                    filename = path_obj.name
                    self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                
                self.end_headers()
                
                # Stream file content
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    
        except IOError:
            self.send_error(500, "Internal server error")
    
    def log_message(self, format, *args):
        """Log requests."""
        print(f"[{self.address_string()}] {format % args}")


def create_handler(content_root):
    """Create handler with content root."""
    class Handler(ContentHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, content_root=content_root, **kwargs)
    return Handler


def main():
    parser = argparse.ArgumentParser(description='Galaxy NG Content Server')
    parser.add_argument('--port', type=int, default=8001, help='Port to listen on')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--content-root', default='/content', help='Content root directory')
    
    args = parser.parse_args()
    
    # Ensure content root exists
    content_root = Path(args.content_root)
    if not content_root.exists():
        print(f"Creating content root: {content_root}")
        content_root.mkdir(parents=True, exist_ok=True)
    
    handler_class = create_handler(args.content_root)
    
    with HTTPServer((args.host, args.port), handler_class) as httpd:
        print(f"Content server starting on {args.host}:{args.port}")
        print(f"Content root: {args.content_root}")
        print("Available endpoints:")
        print("  /health/ - Health check")
        print("  /collections/{ns}/{name}/versions/{version}/download/ - Collection download")
        print("  /namespaces/{namespace}/avatar/ - Namespace avatar")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down content server...")


if __name__ == '__main__':
    main()