#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    fabiorzfreitas_preset.plugin.py
 
    Written by:               Fabiorzfreitas <mckfabio@gmail.com>
    Date:                     Sunday, February 2nd, 2023, 13:00
 
    Copyright:
           Copyright (C) Josh Sunnex - All Rights Reserved
 
           Permission is hereby granted, free of charge, to any person obtaining a copy
           of this software and associated documentation files (the "Software"), to deal
           in the Software without restriction, including without limitation the rights
           to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
           copies of the Software, and to permit persons to whom the Software is
           furnished to do so, subject to the following conditions:
  
           The above copyright notice and this permission notice shall be included in all
           copies or substantial portions of the Software.
  
           THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
           EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
           MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
           IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
           DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
           OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
           OR OTHER DEALINGS IN THE SOFTWARE.

"""

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
  
    abspath = data.get('path')

    logger.debug('------------')
    logger.debug(f'Testing file {abspath}')
    logger.debug('------------')

    # Get file probe
    probe = Probe.init_probe(data, logger, allowed_mimetypes=['video'])
    if not probe:
        # File not able to be probed by ffprobe
        return

    ffprobe_data = probe.get_probe()

    # Get the path to the file

    shared_info = {}

    if os.path.dirname(abspath) == 'Optimized for TV':

        logger.debug(f'File already has been optimized')

        data['add_file_to_pending_tasks'] = False

        return

    for stream in ffprobe_data['streams']:
        
        if stream['codec_type'] == 'video' and stream['codec_name'] != 'h264':

            logger.debug(f'Video stream is not x264')

            shared_info['non_h264'] = True

    if ffprobe_data['streams'][0]['codec_type'] != 'video':
        
        logger.debug(f'File {abspath} does not have video as the first stream, adding to queue')
        data['add_file_to_pending_tasks'] = True
        
        for stream in data['streams']:
            if stream['codec_type'] == 'video':
                shared_info['non_0_video_stream'] = True
                shared_info['video_stream_index'] = stream['index']
                
                return

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

    # Get the path to the file
    abspath = data['original_file_path']

    logger.debug('------------')
    logger.debug(f'Processing file {abspath}')
    logger.debug('------------')

    file_in = data['file_in']
    data['path'] = data['original_file_path']
    data['file_out'] = 'C:\\Users\\Fabio\\Desktop\\samples\\cache\\cache.mkv'
    file_out = data['file_out']
    video_codec = '-c:v:0 copy'

    # Get file probe
    probe = Probe.init_probe(data, logger, allowed_mimetypes=['video'])
    if not probe:
        # File not able to be probed by ffprobe
        return

    ffprobe_data = probe.get_probe()


    # Set the parser
    parser = Parser(logger)
    parser.set_probe(probe)
    data['command_progress_parser'] = parser.parse_progress

    for stream in ffprobe_data['streams']:
        
        if stream['codec_type'] == 'video' and stream['codec_name'] != 'h264':

            logger.debug(f'Video stream is not x264')

            video_codec = '-c:v:0 h264'
            break

    if ffprobe_data['streams'][0]['codec_type'] != 'video':
        
        logger.debug(f'File {abspath} does not have video as the first stream, processing')
        
        for stream in data['streams']:
            if stream['codec_type'] == 'video':
                data['exec_command'] = f'ffmpeg -i {file_in} -map 0:v:0 {video_codec} -map 0:a -c:a copy -sn -map_metadata -1 -map_chapters -1 {file_out}'

        # This doesn't return yet, as a match with other cases is still possible

    if ffprobe_data['streams'][1]['codec_type'] == 'audio' and ffprobe_data['streams'][1]['codec_name'] != 'ac3':
        
        logger.debug(f'File {abspath} does not have ac3 as the first audio stream, processing')
        data['exec_command'] = f'ffmpeg -i {file_in} -map 0:v:0 {video_codec} -map 0:a:0 -c:a:0 ac3 -map 0:a:0 -c:a:1 copy -sn -map_metadata -1 -map_chapters -1 {file_out}'
        
        return

    if video_codec == '-c:v:0 x264':
        
        data['exec_command'] = f'ffmpeg -i {file_in} -map 0:v:0 {video_codec} -map 0:a -c:a copy -sn -map_metadata -1 -map_chapters -1 {file_out}'

        return

    
    for stream in ffprobe_data['streams']:
       
       if stream['codec_type'] == 'subtitle':
            
            logger.debug(f'File {abspath} has subtitles, processing')
            data['exec_command'] = f'ffmpeg -i {file_in} -map 0:v:0 {video_codec} -map 0:a -c:a copy -sn -map_metadata -1 -map_chapters -1 {file_out}'
            
            return
       
       if stream['codec_type'] != 'audio':

            logger.debug(f'File {abspath} has non-audio, non-subtitle stream, likely an attachment, processing')
            data['exec_command'] = f'ffmpeg -i {file_in} -map 0:v:0 {video_codec} -map 0:a -c:a copy -sn -map_metadata -1 -map_chapters -1 {file_out}'

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

    data['path'] = data['source_data']['abspath']

    abspath = data['path']

    logger.debug('------------')
    logger.debug(f'Post-processing file {abspath}')
    logger.debug('------------')

    # Get file probe
    probe = Probe.init_probe(data, logger, allowed_mimetypes=['video'])
    if not probe:
        # File not able to be probed by ffprobe
        return

    ffprobe_data = probe.get_probe()
   
    source_dirpath = f"{os.path.split(data['source_data']['abspath'])[0]}"
    source_dirpath_replaced = source_dirpath.replace('\\', '\\\\')
    show_dir = source_dirpath_replaced.split('\\')[-2]

    data['remove_source_file'] = False
    data['copy_file'] = True
    data['run_default_file_copy'] = False
    data['file_out'] = f'{source_dirpath_replaced}\\test.mkv'
    basename = data['source_data']['basename']

    for stream in ffprobe_data['streams']:
        
        if stream['codec_type'] == 'video' and stream['codec_name'] != 'h264':

            logger.debug(f'Video stream is not x264')

            os.makedirs(f'{source_dirpath_replaced}\\\Plex Versions\\\\Optimized for TV\\\\{show_dir}', exist_ok= True)

            data['file_out'] = f'{source_dirpath_replaced}\\\\Plex Versions\\\\Optimized for TV\\\\{show_dir}{basename}'
            
            break


    return

