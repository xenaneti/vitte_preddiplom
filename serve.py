import argparse
import os

from waitress import serve


def main():
    parser = argparse.ArgumentParser(description='Запуск журнала посещаемости через Waitress')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=int(os.getenv('PORT', '8000')))
    arguments = parser.parse_args()
    from config.wsgi import application
    serve(application, host=arguments.host, port=arguments.port, threads=4,
          max_request_body_size=2 * 1024 * 1024, channel_timeout=60,
          clear_untrusted_proxy_headers=True)


if __name__ == '__main__':
    main()
