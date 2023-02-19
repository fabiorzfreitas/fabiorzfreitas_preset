#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging

from lib.ffmpeg import Probe, Parser, StreamMapper

# Configure plugin logger
logger = logging.getLogger("Unmanic.Plugin.fabiorzfreitas_preset")


def on_library_management_file_test(data):
    """
    Runner function - enables additional actions during the library management file tests.
    The 'data' object argument includes:
        library_id                      - The library that the current task is associated with
        path                            - String containing the full path to the file being tested.
        issues                          - List of currently found issues for not processing the file.
        add_file_to_pending_tasks       - Boolean, is the file currently marked to be added to the queue for processing.
        priority_score                  - Integer, an additional score that can be added to set the position of the new task in the task queue.
        shared_info                     - Dictionary, information provided by previous plugin runners. This can be appended to for subsequent runners.
    :param data:
    :return:
    """

    # Get file probe
    probe = Probe.init_probe(data, logger, allowed_mimetypes=['video'])
    if not probe:
        # File not able to be probed by ffprobe
        return

    ffprobe_data = probe.get_probe()

    # Get the path to the file
    abspath = data.get('path')

    if ffprobe_data[0]['codec_type'] != 'video':
        logger.debug(f'File {abspath} does not have video as the first stream')
        data['add_file_to_pending_tasks'] = True
        return

    if ffprobe_data[1]['codec_type'] == 'audio' and ffprobe_data[1]['codec_name'] != 'ac3':
        logger.debug(f'File {abspath} does not have ac3 as the first audio stream')
        data['add_file_to_pending_tasks'] = True
        return


def on_worker_process(data):
    """
    Runner function - enables additional configured processing jobs during the worker stages of a task.

    The 'data' object argument includes:
        worker_log              - Array, the log lines that are being tailed by the frontend. Can be left empty.
        library_id              - Number, the library that the current task is associated with.
        exec_command            - Array, a subprocess command that Unmanic should execute. Can be empty.
        command_progress_parser - Function, a function that Unmanic can use to parse the STDOUT of the command to collect progress stats. Can be empty.
        file_in                 - String, the source file to be processed by the command.
        file_out                - String, the destination that the command should output (may be the same as the file_in if necessary).
        original_file_path      - String, the absolute path to the original file.
        repeat                  - Boolean, should this runner be executed again once completed with the same variables.

    :param data:
    :return:
    
    """
    return
