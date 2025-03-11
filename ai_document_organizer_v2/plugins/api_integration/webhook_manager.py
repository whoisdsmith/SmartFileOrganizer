"""
Webhook Manager for External API Integration Framework.

This module provides webhook support for event-driven integration with
external APIs, allowing for asynchronous processing of API events.
"""

import logging
import threading
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Union, Callable
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import socketserver
import queue
import hashlib
import hmac
import base64


logger = logging.getLogger(__name__)


class WebhookHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler for webhooks.
    
    Handles incoming webhook requests and forwards them to the
    WebhookManager for processing.
    """
    
    def __init__(self, *args, **kwargs):
        self.webhook_manager = None
        super().__init__(*args, **kwargs)
    
    def set_webhook_manager(self, webhook_manager):
        """Set the webhook manager that will process requests."""
        self.webhook_manager = webhook_manager
    
    def _parse_json_body(self):
        """Parse JSON request body."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length)
                return json.loads(body.decode('utf-8'))
            return {}
        except json.JSONDecodeError:
            return {}
    
    def do_GET(self):
        """Handle GET requests."""
        if not self.webhook_manager:
            self.send_error(500, "Webhook manager not configured")
            return
            
        try:
            # Parse URL and query parameters
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            query_params = parse_qs(parsed_url.query)
            
            # Create event from request
            event = {
                'id': str(uuid.uuid4()),
                'timestamp': time.time(),
                'method': 'GET',
                'path': path,
                'query_params': query_params,
                'headers': dict(self.headers),
                'remote_addr': self.client_address[0],
                'body': None
            }
            
            # Check if this is a verification request
            if self.webhook_manager.is_verification_request(event):
                # Handle verification specially
                response = self.webhook_manager.handle_verification_request(event)
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(response.encode('utf-8'))
                return
                
            # Process the webhook event
            self.webhook_manager.process_webhook_event(event)
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'success'}).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error handling GET webhook: {e}")
            self.send_error(500, str(e))
    
    def do_POST(self):
        """Handle POST requests."""
        if not self.webhook_manager:
            self.send_error(500, "Webhook manager not configured")
            return
            
        try:
            # Parse URL and request body
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            body = self._parse_json_body()
            
            # Create event from request
            event = {
                'id': str(uuid.uuid4()),
                'timestamp': time.time(),
                'method': 'POST',
                'path': path,
                'query_params': {},
                'headers': dict(self.headers),
                'remote_addr': self.client_address[0],
                'body': body
            }
            
            # Verify webhook signature if available
            if not self.webhook_manager.verify_webhook_signature(event):
                self.send_error(401, "Invalid webhook signature")
                return
                
            # Process the webhook event
            self.webhook_manager.process_webhook_event(event)
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'success'}).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error handling POST webhook: {e}")
            self.send_error(500, str(e))


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Threading HTTP server for handling webhook requests."""
    pass


class WebhookManager:
    """
    Manages webhook configuration, server, and event processing.
    
    This class provides functionality to:
    - Start/stop a webhook server
    - Register webhook endpoints
    - Process webhook events
    - Verify webhook signatures
    - Route events to appropriate handlers
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Webhook Manager.
        
        Args:
            config: Optional configuration dictionary for the manager
        """
        self.config = config or {}
        
        # Webhook server settings
        self.server_host = self.config.get('host', '0.0.0.0')
        self.server_port = self.config.get('port', 5000)
        self.server = None
        self.server_thread = None
        self.is_running = False
        
        # Event queue for asynchronous processing
        self.event_queue = queue.Queue()
        self.processing_thread = None
        self.should_process = False
        
        # Webhook registry
        self.webhooks = {}  # type: Dict[str, Dict[str, Any]]
        self.handlers = {}  # type: Dict[str, List[Callable]]
        
        # Security settings
        self.verification_tokens = self.config.get('verification_tokens', {})
        self.signatures = {}  # type: Dict[str, Dict[str, Any]]
        
        logger.info("Webhook Manager initialized")
    
    def start_server(self) -> bool:
        """
        Start the webhook server.
        
        Returns:
            True if the server was started successfully, False otherwise
        """
        if self.is_running:
            logger.warning("Webhook server is already running")
            return True
            
        try:
            # Create webhook handler with reference to this manager
            handler = WebhookHandler
            handler.webhook_manager = self
            
            # Create and start the server
            self.server = ThreadedHTTPServer((self.server_host, self.server_port), handler)
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            # Start event processing thread
            self.should_process = True
            self.processing_thread = threading.Thread(target=self._process_events)
            self.processing_thread.daemon = True
            self.processing_thread.start()
            
            self.is_running = True
            logger.info(f"Webhook server started on {self.server_host}:{self.server_port}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting webhook server: {e}")
            return False
    
    def stop_server(self) -> bool:
        """
        Stop the webhook server.
        
        Returns:
            True if the server was stopped successfully, False otherwise
        """
        if not self.is_running:
            logger.warning("Webhook server is not running")
            return True
            
        try:
            # Stop event processing
            self.should_process = False
            
            # Stop the server
            if self.server:
                self.server.shutdown()
                self.server.server_close()
                self.server = None
                
            self.is_running = False
            logger.info("Webhook server stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping webhook server: {e}")
            return False
    
    def register_webhook(self, 
                        webhook_id: str, 
                        api_name: str,
                        path: str, 
                        description: Optional[str] = None,
                        enabled: bool = True) -> bool:
        """
        Register a webhook endpoint.
        
        Args:
            webhook_id: Unique identifier for the webhook
            api_name: Name of the API associated with this webhook
            path: URL path for the webhook endpoint
            description: Optional description of the webhook
            enabled: Whether the webhook is enabled
            
        Returns:
            True if registration was successful, False otherwise
        """
        if webhook_id in self.webhooks:
            logger.warning(f"Webhook {webhook_id} is already registered")
            return False
            
        # Register the webhook
        self.webhooks[webhook_id] = {
            'id': webhook_id,
            'api_name': api_name,
            'path': path,
            'description': description,
            'enabled': enabled,
            'created_at': time.time()
        }
        
        # Initialize handlers for this webhook
        if webhook_id not in self.handlers:
            self.handlers[webhook_id] = []
            
        logger.info(f"Registered webhook {webhook_id} for path {path}")
        return True
    
    def unregister_webhook(self, webhook_id: str) -> bool:
        """
        Unregister a webhook endpoint.
        
        Args:
            webhook_id: Unique identifier for the webhook
            
        Returns:
            True if unregistration was successful, False otherwise
        """
        if webhook_id not in self.webhooks:
            logger.warning(f"Webhook {webhook_id} is not registered")
            return False
            
        # Unregister the webhook
        del self.webhooks[webhook_id]
        
        # Remove handlers for this webhook
        if webhook_id in self.handlers:
            del self.handlers[webhook_id]
            
        logger.info(f"Unregistered webhook {webhook_id}")
        return True
    
    def register_webhook_handler(self, webhook_id: str, handler: Callable) -> bool:
        """
        Register a handler function for a webhook.
        
        The handler will be called with the webhook event as its argument.
        
        Args:
            webhook_id: Unique identifier for the webhook
            handler: Function to call when a webhook event is received
            
        Returns:
            True if registration was successful, False otherwise
        """
        if webhook_id not in self.webhooks:
            logger.warning(f"Cannot register handler: Webhook {webhook_id} is not registered")
            return False
            
        # Register the handler
        if webhook_id not in self.handlers:
            self.handlers[webhook_id] = []
            
        self.handlers[webhook_id].append(handler)
        logger.info(f"Registered handler for webhook {webhook_id}")
        return True
    
    def unregister_webhook_handler(self, webhook_id: str, handler: Callable) -> bool:
        """
        Unregister a handler function for a webhook.
        
        Args:
            webhook_id: Unique identifier for the webhook
            handler: Handler function to unregister
            
        Returns:
            True if unregistration was successful, False otherwise
        """
        if webhook_id not in self.handlers:
            logger.warning(f"No handlers registered for webhook {webhook_id}")
            return False
            
        try:
            self.handlers[webhook_id].remove(handler)
            logger.info(f"Unregistered handler for webhook {webhook_id}")
            return True
        except ValueError:
            logger.warning(f"Handler not found for webhook {webhook_id}")
            return False
    
    def configure_webhook_signature(self, 
                                   webhook_id: str, 
                                   secret: str,
                                   header_name: str = 'X-Webhook-Signature',
                                   algorithm: str = 'sha256') -> bool:
        """
        Configure signature verification for a webhook.
        
        Args:
            webhook_id: Unique identifier for the webhook
            secret: Secret key for signature verification
            header_name: Name of the header containing the signature
            algorithm: Hash algorithm to use for verification
            
        Returns:
            True if configuration was successful, False otherwise
        """
        if webhook_id not in self.webhooks:
            logger.warning(f"Cannot configure signature: Webhook {webhook_id} is not registered")
            return False
            
        # Store signature configuration
        self.signatures[webhook_id] = {
            'secret': secret,
            'header_name': header_name,
            'algorithm': algorithm
        }
        
        logger.info(f"Configured signature verification for webhook {webhook_id}")
        return True
    
    def set_verification_token(self, api_name: str, token: str) -> bool:
        """
        Set a verification token for an API's webhooks.
        
        Args:
            api_name: Name of the API
            token: Verification token
            
        Returns:
            True if the token was set successfully, False otherwise
        """
        self.verification_tokens[api_name] = token
        logger.info(f"Set verification token for API {api_name}")
        return True
    
    def get_webhook_url(self, webhook_id: str) -> Optional[str]:
        """
        Get the full URL for a webhook.
        
        Args:
            webhook_id: Unique identifier for the webhook
            
        Returns:
            Full URL for the webhook or None if not found
        """
        if webhook_id not in self.webhooks:
            logger.warning(f"Webhook {webhook_id} is not registered")
            return None
            
        webhook = self.webhooks[webhook_id]
        
        # Use configured base URL if available, otherwise construct from server settings
        base_url = self.config.get('base_url')
        if not base_url:
            hostname = self.config.get('hostname', 'localhost')
            port = self.server_port
            base_url = f"http://{hostname}:{port}"
            
        # Construct the full URL
        path = webhook['path']
        if not path.startswith('/'):
            path = f"/{path}"
            
        return f"{base_url}{path}"
    
    def process_webhook_event(self, event: Dict[str, Any]) -> bool:
        """
        Process a webhook event.
        
        This method is called by the webhook handler when a webhook event is received.
        It queues the event for asynchronous processing.
        
        Args:
            event: Dictionary containing the webhook event data
            
        Returns:
            True if the event was queued successfully, False otherwise
        """
        # Find matching webhook based on path
        webhook_id = None
        for wid, webhook in self.webhooks.items():
            if webhook['enabled'] and webhook['path'] == event['path']:
                webhook_id = wid
                break
                
        if not webhook_id:
            logger.warning(f"No webhook registered for path {event['path']}")
            return False
            
        # Add webhook ID to event for processing
        event['webhook_id'] = webhook_id
        
        # Queue the event for asynchronous processing
        try:
            self.event_queue.put(event)
            return True
        except Exception as e:
            logger.error(f"Error queuing webhook event: {e}")
            return False
    
    def _process_events(self):
        """Process webhook events from the queue."""
        while self.should_process:
            try:
                # Get event from queue with timeout to allow thread to exit
                try:
                    event = self.event_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                    
                # Get webhook ID from event
                webhook_id = event.get('webhook_id')
                if not webhook_id or webhook_id not in self.webhooks:
                    logger.warning(f"Invalid webhook ID in event: {webhook_id}")
                    continue
                    
                # Process the event with registered handlers
                if webhook_id in self.handlers:
                    for handler in self.handlers[webhook_id]:
                        try:
                            handler(event)
                        except Exception as e:
                            logger.error(f"Error in webhook handler: {e}")
                            
                # Mark event as processed
                self.event_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing webhook events: {e}")
                time.sleep(1.0)  # Avoid tight loop in case of errors
    
    def verify_webhook_signature(self, event: Dict[str, Any]) -> bool:
        """
        Verify the signature of a webhook event.
        
        Args:
            event: Dictionary containing the webhook event data
            
        Returns:
            True if the signature is valid or no signature verification is configured,
            False if the signature is invalid
        """
        # Find matching webhook based on path
        webhook_id = None
        for wid, webhook in self.webhooks.items():
            if webhook['path'] == event['path']:
                webhook_id = wid
                break
                
        if not webhook_id:
            # No webhook registered for this path, but we'll allow it
            return True
            
        # Check if signature verification is configured for this webhook
        if webhook_id not in self.signatures:
            # No signature verification configured, so we'll accept it
            return True
            
        # Get signature configuration
        sig_config = self.signatures[webhook_id]
        secret = sig_config['secret']
        header_name = sig_config['header_name']
        algorithm = sig_config['algorithm']
        
        # Check if signature header is present
        headers = event['headers']
        signature = headers.get(header_name) or headers.get(header_name.lower())
        if not signature:
            logger.warning(f"No signature header found for webhook {webhook_id}")
            return False
            
        # Verify signature based on algorithm
        try:
            # Get request body as bytes
            body = event.get('body')
            body_str = json.dumps(body) if body else ""
            body_bytes = body_str.encode('utf-8')
            
            # Create HMAC signature
            if algorithm.lower() == 'sha256':
                digest = hmac.new(
                    secret.encode('utf-8'),
                    body_bytes,
                    hashlib.sha256
                ).digest()
            elif algorithm.lower() == 'sha1':
                digest = hmac.new(
                    secret.encode('utf-8'),
                    body_bytes,
                    hashlib.sha1
                ).digest()
            else:
                logger.error(f"Unsupported signature algorithm: {algorithm}")
                return False
                
            # Encode as hex or base64 depending on signature format
            if 'sha' in signature.lower():
                # Hex encoding format (common for GitHub, Stripe, etc.)
                computed_sig = f"sha{algorithm[3:]}=" + hmac.new(
                    secret.encode('utf-8'),
                    body_bytes,
                    getattr(hashlib, algorithm.lower())
                ).hexdigest()
                return computed_sig == signature
            else:
                # Base64 encoding format (common for many services)
                computed_sig = base64.b64encode(digest).decode('utf-8')
                return computed_sig == signature
                
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False
    
    def is_verification_request(self, event: Dict[str, Any]) -> bool:
        """
        Check if an event is a webhook verification request.
        
        Args:
            event: Dictionary containing the webhook event data
            
        Returns:
            True if the event is a verification request, False otherwise
        """
        # GitHub webhook verification
        if 'X-GitHub-Event' in event['headers'] and event['headers'].get('X-GitHub-Event') == 'ping':
            return True
            
        # Facebook webhook verification
        if event['method'] == 'GET' and 'hub.mode' in event['query_params'] and 'hub.verify_token' in event['query_params']:
            return True
            
        # Stripe webhook verification
        if event['method'] == 'POST' and event['headers'].get('Stripe-Signature') and not event['body']:
            return True
            
        # Custom verification parameter
        if event['method'] == 'GET' and 'verify' in event['query_params']:
            return True
            
        return False
    
    def handle_verification_request(self, event: Dict[str, Any]) -> str:
        """
        Handle a webhook verification request.
        
        Args:
            event: Dictionary containing the webhook event data
            
        Returns:
            Response string to return to the requester
        """
        # Find matching webhook based on path
        webhook_id = None
        api_name = None
        for wid, webhook in self.webhooks.items():
            if webhook['path'] == event['path']:
                webhook_id = wid
                api_name = webhook['api_name']
                break
                
        if not webhook_id or not api_name:
            logger.warning(f"No webhook registered for path {event['path']}")
            return "Webhook verification failed: Unknown webhook"
            
        # GitHub webhook verification
        if 'X-GitHub-Event' in event['headers'] and event['headers'].get('X-GitHub-Event') == 'ping':
            return json.dumps({"message": "Webhook verification successful"})
            
        # Facebook webhook verification
        if event['method'] == 'GET' and 'hub.mode' in event['query_params'] and 'hub.verify_token' in event['query_params']:
            mode = event['query_params']['hub.mode'][0]
            token = event['query_params']['hub.verify_token'][0]
            challenge = event['query_params'].get('hub.challenge', [''])[0]
            
            if mode == 'subscribe' and token == self.verification_tokens.get(api_name, ''):
                return challenge
            else:
                return "Webhook verification failed: Invalid verification token"
                
        # Custom verification parameter
        if event['method'] == 'GET' and 'verify' in event['query_params']:
            token = event['query_params']['verify'][0]
            
            if token == self.verification_tokens.get(api_name, ''):
                return "Webhook verification successful"
            else:
                return "Webhook verification failed: Invalid verification token"
                
        return "Webhook verification failed: Unknown verification method"
    
    def get_webhook_info(self, webhook_id: str) -> Dict[str, Any]:
        """
        Get information about a webhook.
        
        Args:
            webhook_id: Unique identifier for the webhook
            
        Returns:
            Dictionary with webhook information
        """
        if webhook_id not in self.webhooks:
            return {
                'id': webhook_id,
                'registered': False
            }
            
        webhook = self.webhooks[webhook_id].copy()
        webhook['url'] = self.get_webhook_url(webhook_id)
        webhook['handler_count'] = len(self.handlers.get(webhook_id, []))
        webhook['has_signature_verification'] = webhook_id in self.signatures
        
        return webhook
    
    def get_all_webhooks(self) -> List[Dict[str, Any]]:
        """
        Get information about all registered webhooks.
        
        Returns:
            List of dictionaries with webhook information
        """
        return [self.get_webhook_info(webhook_id) for webhook_id in self.webhooks]