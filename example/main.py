import os
import sys
import logging
from fastapi import FastAPI


import logging


def setup_logging():
    log_format = (
        "%(levelname)s: [%(asctime)s][%(name)s][%(filename)s::%(lineno)s] %(message)s"
    )

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )


app = FastAPI()

# setup_logging()

logging.info("lovely weather eh")


@app.get("/")
def get_main():
    return {"status": "OK"}
