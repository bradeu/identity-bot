from celery import signals
from utils.keepalive import KeepAlive


@signals.task_prerun.connect
def _kickoff_keepalive(*args, **kwargs):
    KeepAlive.start()


@signals.task_postrun.connect
def _halt_keepalive(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    # When the very last task finishes, worker is idle ⇒ stop pinger
    try:
        if sender and hasattr(sender, 'app') and sender.app.control.inspect().active():  # any tasks still running?
            return
        KeepAlive.stop()
    except Exception as e:
        # Silently handle any inspection errors
        pass
