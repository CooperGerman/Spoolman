"""Main entrypoint to the server."""

import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from platformdirs import user_data_dir
from sqlalchemy import URL

from spoolman import env
from spoolman.api.v1.router import app as v1_app
from spoolman.database.database import setup_db

# Get the data directory
data_dir = Path(user_data_dir("spoolman"))
data_dir.mkdir(parents=True, exist_ok=True)

# Setup file logger
logging.basicConfig(
    filename=data_dir.joinpath("spoolman.log"),
    filemode="w",
    format="%(asctime)s:%(levelname)s:%(message)s",
    datefmt="%Y-%m-%d %I:%M:%S%p",
)

# Setup the base logger
spoolman_logger = logging.getLogger("spoolman")
spoolman_logger.setLevel(env.get_logging_level())

# Log all messages to console
formatter = logging.Formatter("%(name)-12s: %(levelname)-8s %(message)s")
console = logging.StreamHandler()
console.setLevel(env.get_logging_level())
console.setFormatter(formatter)
root_logger = logging.getLogger("")
root_logger.addHandler(console)

# Get logger instance
logger = logging.getLogger(__name__)

# Setup FastAPI
app = FastAPI(debug=env.is_debug_mode())
app.mount("/api/v1", v1_app)
app.mount("/", StaticFiles(directory="client/dist", html=True), name="client")

# Allow all origins if in debug mode
if env.is_debug_mode():
    logger.warning("Running in debug mode, allowing all origins.")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def get_connection_url() -> URL:
    """Construct the connection URL for the database based on environment variables."""
    db_type = env.get_database_type()
    host = env.get_host()
    port = env.get_port()
    database = env.get_database()
    query = env.get_query()
    username = env.get_username()
    password = env.get_password()

    if db_type is None:
        db_type = env.DatabaseType.SQLITE
        database = str(data_dir.joinpath("spoolman.db"))
        logger.info('No database type specified, using a default SQLite database located at "%s"', database)
    else:
        logger.info('Connecting to database of type "%s" at "%s:%s"', db_type, host, port)

    return URL.create(
        drivername=db_type.to_drivername(),
        host=host,
        port=port,
        database=database,
        query=query or {},
        username=username,
        password=password,
    )


@app.on_event("startup")
async def startup() -> None:
    """Run the service's startup sequence."""
    await setup_db(get_connection_url())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
