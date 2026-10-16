"""Background task exception capture, without exposing tokens."""
import asyncio
import logging

log=logging.getLogger("mop.background")

def install_loop_handler(loop):
    previous=loop.get_exception_handler()
    def handler(loop,context):
        exception=context.get("exception")
        log.error("Unhandled background exception: %s",context.get("message","unknown"),exc_info=(type(exception),exception,exception.__traceback__) if exception else None)
        if previous:
            previous(loop,context)
    loop.set_exception_handler(handler)
