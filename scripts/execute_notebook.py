#!/usr/bin/env python3
"""Execute every notebook cell using the current environment, fail on any error."""
from pathlib import Path
import sys
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

root=Path(__file__).resolve().parents[1]
path=root/'materials/ORBIT_Action_Planning.ipynb'
notebook=nbformat.read(path,as_version=4)
manager=KernelManager(kernel_name='python3')
# Bind to this interpreter rather than an unrelated globally registered kernel.
manager.kernel_spec.argv=[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}']
client=NotebookClient(notebook,km=manager,timeout=180,resources={'metadata':{'path':str(root)}})
try:
    client.execute()
finally:
    if manager.has_kernel:
        manager.shutdown_kernel(now=True)
    manager.cleanup_resources()
nbformat.write(notebook,path)
print('Executed',sum(c.cell_type=='code' for c in notebook.cells),'code cells without errors')
