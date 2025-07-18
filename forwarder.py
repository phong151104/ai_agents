import re
from datetime import datetime
from fastapi import Request
from fastapi import APIRouter

import app.util.utils
from app.service import nq57_client
from app.service.nq57_client import GetSortedMissionList, map_status_label_to_key, get_kh02_tracking_results
from app.util import date_utils

router = APIRouter()
