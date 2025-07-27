import uvicorn
import click
from common.settings import settings

@click.command()
@click.option("--host", default=settings.GATEWAY_SERVER_HOST, help="Host to bind the Gateway server to.")
@click.option("--port", default=settings.GATEWAY_SERVER_PORT, type=int, help="Port for the Gateway server.")
def main(host: str, port: int):
    """Starts the AgriConnect Gateway Server."""
    # The format 'module_name:app_instance_name' is how uvicorn loads the app.
    # Set reload=False for production/container environments
    uvicorn.run("gateway_server.server:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    main()