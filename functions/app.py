import json
from flask import Flask, request
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.wrappers import Response
from app import create_app  # Make sure to replace this with your actual import

app = create_app()

def handler(event, context):
    # Create a WSGI environment from the event
    environ = {
        'REQUEST_METHOD': event['httpMethod'],
        'SCRIPT_NAME': '',
        'PATH_INFO': event['path'],
        'QUERY_STRING': '',
        'CONTENT_TYPE': event.get('headers', {}).get('content-type', ''),
        'CONTENT_LENGTH': event.get('headers', {}).get('content-length', ''),
        'wsgi.input': event['body'] if 'body' in event else '',
        'wsgi.errors': '',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'http',
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': True,
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': '80',
    }

    # Create a response function
    def start_response(status, response_headers, exc_info=None):
        return Response(status=status, headers=dict(response_headers))

    # Dispatch request to Flask application
    response = DispatcherMiddleware(app, {
        '/': app
    })(environ, start_response)

    return {
        'statusCode': response.status_code,
        'headers': dict(response.headers),
        'body': response.get_data(as_text=True)
    }
