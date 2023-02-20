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
from fabiorzfreitas_preset.lib.ffmpeg import Probe, Parser, StreamMapper

# Configures plugin logger
logger = logging.getLogger("Unmanic.Plugin.fabiorzfreitas_preset")

# Formats logger output
def logger_output(line):
    line_len = '-' * len(line)

    logger.debug(line_len)
    logger.debug(line)
    logger.debug(line_len)

    return


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
    
    # Sets working path
    abspath = data.get('path')

    line = f'[TESTING] Testing file {abspath}'
    logger_output(line)

    # Skips cache files
    if os.path.basename(abspath).split('.')[-2] == 'cache':
        
        line = f'[TESTING] File {abspath} is cache, skipping'
        logger_output(line)
        
        data['add_file_to_pending_tasks'] = False

        return

    # Skips .part files
    if os.path.splitext(abspath)[1] == '.part':
        
        line = f'[TESTING] File {abspath} extension is .part, skipping'
        logger_output(line)
        
        data['add_file_to_pending_tasks'] = False

        return

    # Gets file probe
    probe = Probe.init_probe(data, logger, allowed_mimetypes=['video'])
    if not probe:
        # File not able to be probed by ffprobe
        return

    ffprobe_data = probe.get_probe()

    # Defines paths and shared_info
    shared_info = {}
    source_dirpath = f"{os.path.split(data['path'])[0]}"
    source_dirpath_replaced = source_dirpath.replace('\\', '/')
    show_dir = source_dirpath_replaced.split('/')[-2]
    basename = f"{os.path.split(data['path'])[1]}"

    # Tests if file is already in Optimized folder
    if show_dir == 'Optimized for TV' or os.path.exists(f'{source_dirpath_replaced}/Plex Versions/Optimized for TV/{show_dir}/{basename}'):

        line = f'[TESTING] File {abspath} already has been optimized, skipping'
        logger_output(line)
        
        data['add_file_to_pending_tasks'] = False

        return
    
    # Tests if container is .mkv
    # A second pass will be needed if this matches
    if os.path.splitext(abspath)[1] != '.mkv':

        line = f'[TESTING] File {abspath} container is not .mkv, adding to queue'
        logger_output(line)

        data['add_file_to_pending_tasks'] = True
        shared_info['container_is_not_mkv'] = True

        return

    # Checks the first video stream for x264
    for stream in ffprobe_data['streams']:
        
        if stream['codec_type'] == 'video' and stream['codec_name'] != 'h264':

            line = f'[TESTING] File {abspath} video stream is not x264, adding to queue'
            logger_output(line)

            shared_info['non_h264'] = True
            # This function doesn't return yet, as the file still needs to be checked for audio

    # Checks if the video stream is the first stream
    if ffprobe_data['streams'][0]['codec_type'] != 'video':
        
        line = f'[TESTING] File {abspath} does not have video as the first stream, adding to queue'
        logger_output(line)
        
        data['add_file_to_pending_tasks'] = True
        
        for stream in data['streams']:
            if stream['codec_type'] == 'video':
                shared_info['non_0_video_stream'] = True
                shared_info['video_stream_index'] = stream['index']
                
                break
                # This function doesn't return yet, as the file still needs to be checked for audio

    # Checks if first audio stream is ac3
    if ffprobe_data['streams'][1]['codec_type'] == 'audio' and ffprobe_data['streams'][1]['codec_name'] != 'ac3':
        
        line = f'[TESTING] File {abspath} does not have ac3 as the first audio stream, adding to queue'
        logger_output(line)

        data['add_file_to_pending_tasks'] = True
        shared_info['first_audio_is_not_ac3'] = True
        
        return
    
    # Checks if there are chapters
    if ffprobe_data['chapters'] != []:

        line = f'[TESTING] File {abspath} has chapters, processing'
        logger_output(line)

        data['add_file_to_pending_tasks'] = True
        shared_info['has_chapters'] = True

        return

    # Checks streams for subtitles, attachments and metadata
    for stream in ffprobe_data['streams']:
       
        if stream['codec_type'] == 'subtitle':
            
            line = f'[TESTING] File {abspath} has subtitles, adding to queue'
            logger_output(line)

            data['add_file_to_pending_tasks'] = True
            shared_info['has_subtitles'] = True
            
            return
       
        if stream['codec_type'] != 'audio' and stream['codec_type'] != 'video':

            line = f'[TESTING] File {abspath} has non-audio, non-subtitle stream, likely an attachment, adding to queue'
            logger_output(line)

            data['add_file_to_pending_tasks'] = True
            shared_info['has_attachment'] = True

            return

        allowed_tags = ['language', 'DURATION', 'ENCODER']
        if not set(stream['tags'].keys()).issubset(allowed_tags):
            
            line = f'[TESTING] File {abspath} has unwanted metadata, adding to queue'
            logger_output(line)

            data['add_file_to_pending_tasks'] = True
            shared_info['has_unwanted_metadata'] = True

            return

    # If file passes all checks, it's skipped    
    line = f"File {abspath} doesn't need processing, skipping"
    logger_output(line)
    
    data['add_file_to_pending_tasks'] = False
    return
            

def on_worker_process(data):
    """
    Runner function - enables additional configured processing jobs during the worker stages of a task.

    The 'data' object argument includes:
        worker_log              - Array, the log line_lens that are being tailed by the frontend. Can be left empty.
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

    line = f'[PROCESSING] Processing file {abspath}'
    logger_output(line)

    # Defines working variables
    path, basename = os.path.split(abspath)   
    no_ext = os.path.splitext(basename)[0] 
    file_in = data['file_in']
    data['path'] = data['original_file_path']
    data['file_out'] = f'{path}/{no_ext}.cache.mkv'
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

    # Tests if container is .mkv
    # A second pass will be needed if this matches
    if os.path.splitext(abspath)[1] != '.mkv':

        line = f'[PROCESSING] File {abspath} container is not .mkv, processing'
        logger_output(line)

        data['exec_command'] = f'ffmpeg -i {file_in} -c copy {file_out}'

        return
        
    # Checks the first video stream for x264
    for stream in ffprobe_data['streams']:
        
        if stream['codec_type'] == 'video' and stream['codec_name'] != 'h264':

            line = f'[PROCESSING] File {abspath} video stream is not x264, setting video codec'
            logger_output(line)

            video_codec = '-c:v:0 h264'
            break
            # This function doesn't return yet, as the file still needs to be checked for audio
        
    # Checks if the video stream is the first stream
    if ffprobe_data['streams'][0]['codec_type'] != 'video':
        
        line = f'[PROCESSING] File {abspath} does not have video as the first stream, processing'
        logger_output(line)
        
        for stream in data['streams']:
            if stream['codec_type'] == 'video':
                data['exec_command'] = f'ffmpeg -i {file_in} -map 0:v:0 {video_codec} -map 0:a -c:a copy -sn -map_metadata -1 -map_chapters -1 {file_out}'
    
    # Checks if first audio stream is ac3
    if ffprobe_data['streams'][1]['codec_type'] == 'audio' and ffprobe_data['streams'][1]['codec_name'] != 'ac3':
        
        line = f'[PROCESSING] File {abspath} does not have ac3 as the first audio stream, processing'
        logger_output(line)

        data['exec_command'] = f'ffmpeg -i {file_in} -map 0:v:0 {video_codec} -map 0:a:0 -c:a:0 ac3 -map 0:a:0 -c:a:1 copy -sn -map_metadata -1 -map_chapters -1 {file_out}'
        
        return
    
    # If video check matches, processing starts after checking audio
    if video_codec == '-c:v:0 x264':
        
        data['exec_command'] = f'ffmpeg -i {file_in} -map 0:v:0 {video_codec} -map 0:a -c:a copy -sn -map_metadata -1 -map_chapters -1 {file_out}'

        return

    # Checks if there are chapters
    if ffprobe_data['chapters'] != []:

        line = f'[PROCESSING] File {abspath} has chapters, processing'
        logger_output(line)

        data['exec_command'] = f'ffmpeg -i {file_in} -map 0:v:0 {video_codec} -map 0:a -c:a copy -sn -map_metadata -1 -map_chapters -1 {file_out}'

        return
    
    # Checks streams for subtitles, attachments and metadata
    for stream in ffprobe_data['streams']:
       
        if stream['codec_type'] == 'subtitle':
            
            line = f'[PROCESSING] File {abspath} has subtitles, processing'
            logger_output(line)

            data['exec_command'] = f'ffmpeg -i {file_in} -map 0:v:0 {video_codec} -map 0:a -c:a copy -sn -map_metadata -1 -map_chapters -1 {file_out}'
            
            return
       
        if stream['codec_type'] != 'audio' and stream['codec_type'] != 'video':

            line = f'[PROCESSING] File {abspath} has non-audio, non-subtitle stream, likely an attachment, processing'
            logger_output(line)

            data['exec_command'] = f'ffmpeg -i {file_in} -map 0:v:0 {video_codec} -map 0:a -c:a copy -sn -map_metadata -1 -map_chapters -1 {file_out}'

            return

        allowed_tags = ['language', 'DURATION', 'ENCODER']
        if not set(stream['tags'].keys()).issubset(allowed_tags):
            
            line = f'[PROCESSING] File {abspath} has unwanted metadata, processing'
            logger_output(line)

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

    # Defines paths
    data['path'] = data['source_data']['abspath']
    abspath = data['path']
    source_dirpath = f"{os.path.split(data['source_data']['abspath'])[0]}"
    source_dirpath_replaced = source_dirpath.replace('\\', '/')
    show_dir = source_dirpath_replaced.split('/')[-2]
    basename = data['source_data']['basename']


    line = f'[POST-PROCESSING] Post-processing file {abspath}'
    logger_output(line)

    # Get file probe
    probe = Probe.init_probe(data, logger, allowed_mimetypes=['video'])
    if not probe:
        # File not able to be probed by ffprobe
        return

    ffprobe_data = probe.get_probe()
   
    # Sets function parameters
    data['remove_source_file'] = False
    data['copy_file'] = True
    data['run_default_file_copy'] = False
    data['file_out'] = f'{source_dirpath_replaced}/{basename}'

    # Resets output location for files with a new container
    if os.path.splitext(abspath)[1] != '.mkv':

        line = f'[POST-PROCESSING] File {abspath} container is now .mkv, moving'
        logger_output(line)

        data['remove_source_file'] = True
        data['run_default_file_copy'] = True

        return

    # Sets Plex Optimized Versions as output folder for x264 transcodes
    for stream in ffprobe_data['streams']:
        
        if stream['codec_type'] == 'video' and stream['codec_name'] != 'h264':

            line = f'[POST-PROCESSING] File {abspath} video stream is not x264, setting different output'
            logger_output(line)

            os.makedirs(f'{source_dirpath_replaced}/Plex Versions/Optimized for TV/{show_dir}', exist_ok= True)

            data['file_out'] = f'{source_dirpath_replaced}/Plex Versions/Optimized for TV/{show_dir}/{basename}'
            
            break

    return

