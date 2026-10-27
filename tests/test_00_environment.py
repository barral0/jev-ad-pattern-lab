"""Route ephemeral test probes to the agent scratch dir when present."""
import os, tempfile
from pathlib import Path
scratch=Path.home()/'AppData/Local/hermes/profiles/atlas---supervisor-de-operacoes/cache/scratch'
if scratch.is_dir():
    tempfile.tempdir=str(scratch)
    os.environ['TMPDIR']=str(scratch)
    os.environ['TEMP']=str(scratch)
    os.environ['TMP']=str(scratch)
