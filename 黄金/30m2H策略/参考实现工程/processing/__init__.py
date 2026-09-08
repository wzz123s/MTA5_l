# -*- coding: utf-8 -*-
"""processing - Data processing pipeline"""
from processing.smma import calc_smma
from processing.direction import mark_direction
from processing.segment_filter import filter_short_segments_v2
from processing.way_grade import way_grade
from processing.extrema import track_segment_extrema
from processing.prepare import prepare
