import logging
import smtp_server
import asyncio

logging.basicConfig(level=logging.INFO)

def main():
    print("Starting Standalone SMTP on 2526...")
    c = smtp_server.start_smtp_server(port=2526)
    try:
        loop = asyncio.get_event_loop()
        loop.run_forever()
    except KeyboardInterrupt:
        c.stop()

if __name__ == "__main__":
    main()
