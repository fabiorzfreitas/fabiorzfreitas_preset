#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging

import os
import sys
from fabiorzfreitas_preset.lib.ffmpeg import Probe, Parser, StreamMapper

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

    shared_info = {}

    if ffprobe_data['streams'][0]['codec_type'] != 'video':
        
        logger.debug(f'File {abspath} does not have video as the first stream, adding to queue')
        data['add_file_to_pending_tasks'] = True
        
        for stream in data['streams']:
            if stream['codec_type'] == 'video':
                shared_info['non_0_video_stream'] = True
                shared_info['video_stream_index'] = stream['index']
        # This doesn't return yet, as a match with other cases is still possible

    if ffprobe_data['streams'][1]['codec_type'] == 'audio' and ffprobe_data['streams'][1]['codec_name'] != 'ac3':
        
        logger.debug(f'File {abspath} does not have ac3 as the first audio stream, adding to queue')
        data['add_file_to_pending_tasks'] = True
        shared_info['first_audio_is_not_ac3'] = True
        
        return

    for stream in ffprobe_data['streams']:
       
       if stream['codec_type'] == 'subtitle':
            
            logger.debug(f'File {abspath} has subtitles, adding to queue')
            data['add_file_to_pending_tasks'] = True
            shared_info['has_subtitles'] = True
            
            return
       
       if stream['codec_type'] != 'audio':

            logger.debug(f'File {abspath} has non-audio, non-subtitle stream, likely an attachment, adding to queue')
            data['add_file_to_pending_tasks'] = True
            shared_info['has_attachment'] = True

            return

    logger.debug(f"File {abspath} doesn't need processing, skipping")
    data['add_file_to_pending_tasks'] = False
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

    file_in = data['file_in']
    data['path'] = data['original_file_path']
    data['file_out'] = 'C:\\Users\\Fabio\\Desktop\\samples\\cache.mkv'
    file_out = data['file_out']


    # Get file probe
    probe = Probe.init_probe(data, logger, allowed_mimetypes=['video'])
    if not probe:
        # File not able to be probed by ffprobe
        return

    ffprobe_data = probe.get_probe()

    # Get the path to the file
    abspath = data.get('original_file_path')

    # Set the parser
    parser = Parser(logger)
    parser.set_probe(probe)
    data['command_progress_parser'] = parser.parse_progress

    if ffprobe_data['streams'][0]['codec_type'] != 'video':
        
        logger.debug(f'File {abspath} does not have video as the first stream, processing')
        
        for stream in data['streams']:
            if stream['codec_type'] == 'video':
                data['exec_command'] = f'ffmpeg -i {file_in} -map 0:v:0 -c:v:0 copy -map 0:a -c:a copy -sn -map_metadata -1 -map_chapters -1 {file_out}'

        # This doesn't return yet, as a match with other cases is still possible

    if ffprobe_data['streams'][1]['codec_type'] == 'audio' and ffprobe_data['streams'][1]['codec_name'] != 'ac3':
        
        logger.debug(f'File {abspath} does not have ac3 as the first audio stream, processing')
        data['exec_command'] = f'ffmpeg -i {file_in} -map 0:v:0 -c:v:0 copy -map 0:a:0 -c:a:0 ac3 -map 0:a:0 -c:a:1 copy -sn -map_metadata -1 -map_chapters -1 {file_out}'
        
        return

    for stream in ffprobe_data['streams']:
       
       if stream['codec_type'] == 'subtitle':
            
            logger.debug(f'File {abspath} has subtitles, processing')
            data['exec_command'] = f'ffmpeg -i {file_in} -map 0:v:0 -c:v:0 copy -map 0:a -c:a copy -sn -map_metadata -1 -map_chapters -1 {file_out}'
            
            return
       
       if stream['codec_type'] != 'audio':

            logger.debug(f'File {abspath} has non-audio, non-subtitle stream, likely an attachment, processing')
            data['exec_command'] = f'ffmpeg -i {file_in} -map 0:v:0 -c:v:0 copy -map 0:a -c:a copy -sn -map_metadata -1 -map_chapters -1 {file_out}'

            return

    return


def on_postprocessor_file_movement(data):
    """
    Runner function - configures additional postprocessor file movements during the postprocessor stage of a task.

    The 'data' object argument includes:
        source_data             - Dictionary containing data pertaining to the original source file.
        remove_source_file      - Boolean, should Unmanic remove the original source file after all copy operations are complete.
        copy_file               - Boolean, should Unmanic run a copy operation with the returned data variables.
        file_in                 - The converted cache file to be copied by the postprocessor.
        file_out                - The destination file that the file will be copied to.

    :param data:
    :return:
    """

    data['remove_source_file'] = False
    data['copy_file'] = True
    data['run_default_file_copy'] = False

    source_dir = f"{os.path.split(data['source_data']['abspath'])[0]}"
    source_dir_replaced = source_dir.replace('\\', '\\\\')

    data['file_out'] = f'{source_dir_replaced}\\test.mkv'

    return