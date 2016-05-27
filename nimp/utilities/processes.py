# -*- coding: utf-8 -*-

import os
import os.path
import subprocess
import threading
import time
import logging

from nimp.utilities.system import *
from nimp.utilities.windows_utilities import *

#-------------------------------------------------------------------------------
def _default_log_callback(line, log_level):
    log_message(log_level, False, line)

#-------------------------------------------------------------------------------
def _sanitize_command(command):
    new_command = []
    for x in command:
        # If we’re running under MSYS, leading slashes in command line arguments
        # will be treated as a path, so we need to escape them, except if the given
        # argument is indeed a file.
        if x[0:1] == '/':
            if is_msys():
                # If the argument starts with /, we may wish to rewrite it
                if x[1:2].isalpha() and x[2:3] == '/':
                    # Stuff like /c/... looks like a path with a drive letter, keep it that way
                    # XXX: but /c is most probably a flag, so that one needs to be escaped
                    pass
                elif len(x) > 5 and (os.path.isfile(x) or os.path.isdir(x)):
                    pass
                else:
                    x = '/' + x
        new_command.append(x)
    return new_command

#-------------------------------------------------------------------------------
def capture_process_output(directory, command, input = None, encoding = 'utf-8'):
    command = _sanitize_command(command)
    logging.debug("Running “%s” in “%s”", " ".join(command), os.path.abspath(directory))
    process = subprocess.Popen(command,
                               cwd     = directory,
                               stdout  = subprocess.PIPE,
                               stderr  = subprocess.PIPE,
                               stdin   = subprocess.PIPE,
                               bufsize = 1)
    output, error = process.communicate(input.encode(encoding) if input else None)

    return process.wait(), output.decode(encoding), error.decode(encoding)

#-------------------------------------------------------------------------------
def call_process(directory, command, heartbeat = 0):
    command = _sanitize_command(command)
    logging.debug("Running “%s” in “%s”", " ".join(command), os.path.abspath(directory))

    if is_windows():
        disable_win32_dialogs()
        debug_pipe = OutputDebugStringLogger()

    # The bufsize = 1 is important; if we don’t bufferise the
    # output, we’re going to make the callee lag a lot.
    process = subprocess.Popen(command,
                               cwd     = directory,
                               stdout  = subprocess.PIPE,
                               stderr  = subprocess.PIPE,
                               stdin   = None,
                               bufsize = 1)
    if is_windows():
        debug_pipe.attach(process.pid)
        debug_pipe.start()

    def heartbeat_worker(heartbeat):
        t = time.monotonic()
        while process:
            if heartbeat > 0 and time.monotonic() > t + heartbeat:
                logging.info("Keepalive for %s", command[0])
                t += heartbeat
            time.sleep(0.050)

    def output_worker(log_function, pipe):
        output_buffer = ""
        # FIXME: it would be better to use while process.poll() == None
        # here, but thread safety issues in Python < 3.4 prevent it.
        while process:
            try:
                for line in iter(pipe.readline, ''):
                    try:
                        line = line.decode("utf-8")
                    except:
                        line = line.decode("cp850")

                    if line == '':
                        break

                    line = line.replace("{", "{{").replace("}", "}}")
                    line = line.rstrip('\r\n')

                    log_function(line)

                # Sleep for 10 milliseconds if there was no data,
                # or we’ll hog the CPU.
                time.sleep(0.010)

            except ValueError:
                return

    log_thread_args = [ (logging.debug, process.stdout),
                        (logging.error, process.stderr) ]
    if is_windows():
        log_thread_args += [ (logging.debug, debug_pipe.output) ]

    worker_threads = [ threading.Thread(target = output_worker, args = args) for args in log_thread_args ]
    # Send keepalive to stderr if requested
    if heartbeat > 0:
        worker_threads += [ threading.Thread(target = heartbeat_worker, args = (heartbeat, )) ]

    for thread in worker_threads:
        thread.start()

    try:
        process_return = process.wait()
    finally:
        process = None
        if is_windows():
            debug_pipe.stop()
        for thread in worker_threads:
            thread.join()

    if process_return == 0:
        log = log_verbose
    else:
        log = log_error
    logging.info("Program “%s” finished with exit code %s", command[0], process_return)

    return process_return

