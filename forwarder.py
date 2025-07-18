import re
from datetime import datetime
from fastapi import Request
from fastapi import APIRouter

import app.util.utils
from app.service import nq57_client
from app.service.nq57_client import GetSortedMissionList, map_status_label_to_key, get_kh02_tracking_results
from app.util import date_utils

router = APIRouter()


@router.post("/nq57/mission/list")
async def nq57_mission_list(model: nq57_client.GetMissionRequest):
    def to_list(val):
        if isinstance(val, list):
            return [str(v).strip() for v in val if v is not None and str(v).strip()]
        if isinstance(val, str):
            return [v.strip() for v in val.split(",") if v.strip()]
        return []

    # Mapping tiếng Việt sang key backend đúng với API/data trả về
    status_map = {
        "chưa thực hiện đúng hạn": "chua_thuc_hien_dung_han",
        "chưa thực hiện quá hạn": "chua_thuc_hien_qua_han",
        "đã thực hiện đúng hạn": "da_hoan_thanh_dung_han",
        "đã thực hiện quá hạn": "da_hoan_thanh_qua_han",
        "đã hoàn thành đúng hạn": "da_hoan_thanh_dung_han",
        "đã hoàn thành quá hạn": "da_hoan_thanh_qua_han",
        "đang thực hiện đúng hạn": "dang_thuc_hien_dung_han",
        "đang thực hiện quá hạn": "dang_thuc_hien_qua_han"
    }

    _model = nq57_client.GetMissionListRequest()
    if model.loai_nhiem_vu and len(str(model.loai_nhiem_vu).strip()) > 0:
        _model.loai_nhiem_vu = [item.strip() for item in str(model.loai_nhiem_vu).split(",") if item.strip()]
    if model.nhom_nhiem_vu and len(str(model.nhom_nhiem_vu).strip()) > 0:
        _model.nhom_nhiem_vu = [item.replace("Nhóm", "").strip() for item in str(model.nhom_nhiem_vu).split(",")]
        nhom_nhiem_vu = []
        for item in _model.nhom_nhiem_vu:
            if re.match(r"\d+", item):
                match = re.findall(r"\d+", item)[0]
                nhom_nhiem_vu.append(app.util.utils.int_to_roman(int(match)))
            else:
                nhom_nhiem_vu.append(item)
        _model.nhom_nhiem_vu = nhom_nhiem_vu
    if model.don_vi_thuc_hien and len(str(model.don_vi_thuc_hien).strip()) > 0:
        _model.don_vi_thuc_hien = [item.strip() for item in str(model.don_vi_thuc_hien).split(",") if item.strip()]
    if model.ky_bao_cao_from and len(str(model.ky_bao_cao_from).strip()) > 0:
        _model.ky_bao_cao_from = str(model.ky_bao_cao_from).strip()
    if model.ky_bao_cao_to and len(str(model.ky_bao_cao_to).strip()) > 0:
        _model.ky_bao_cao_to = str(model.ky_bao_cao_to).strip()

    # Chuẩn hóa trạng thái sang key backend (giữ đúng thứ tự bạn truyền vào)
    if hasattr(model, "trang_thai") and model.trang_thai:
        _raw_trang_thai = to_list(model.trang_thai)
        status = []
        for item in _raw_trang_thai:
            key = item.strip().lower()
            if key in status_map:
                status.append(status_map[key])
            else:
                status.append(key)
        _model.trang_thai = status

    if not _model.ky_bao_cao_from and not _model.ky_bao_cao_to:
        return await nq57_client.get_missions_latest(_model)
    if not _model.don_vi_thuc_hien:
        # Nếu không có nhóm nhiệm vụ (rỗng hoặc empty list)
        if _model.nhom_nhiem_vu and len(_model.nhom_nhiem_vu) > 0:
            return await nq57_client.get_missions_not_dv_with_group(_model)
        else:
            return await nq57_client.get_missions_not_dv_no_group(_model)
    return await nq57_client.get_missions(_model)

@router.post("/kh02/mission/list")
async def kh02_tracking(model: nq57_client.KH02TrackingRequest):
    # Helper: normalize to list of strings
    def to_list(val):
        if isinstance(val, (list, tuple, set)):
            return [str(x).strip() for x in val if x is not None and str(x).strip()]
        if isinstance(val, str):
            return [x.strip() for x in val.split(",") if x.strip()]
        return []

    status_map = {
        "chưa thực hiện đúng hạn": "chua_thuc_hien_dung_han",
        "chưa thực hiện quá hạn": "chua_thuc_hien_qua_han",
        "đã thực hiện đúng hạn": "da_hoan_thanh_dung_han",
        "đã thực hiện quá hạn": "da_hoan_thanh_qua_han",
        "đã hoàn thành đúng hạn": "da_hoan_thanh_dung_han",
        "đã hoàn thành quá hạn": "da_hoan_thanh_qua_han",
        "đang thực hiện đúng hạn": "dang_thuc_hien_dung_han",
        "đang thực hiện quá hạn": "dang_thuc_hien_qua_han"
    }
    # Build internal request model
    _model = nq57_client.KH02TrackingRequest()

    # Đơn vị thực hiện
    if model.don_vi_thuc_hien:
        _model.don_vi_thuc_hien = to_list(model.don_vi_thuc_hien)

    # Loại nhiệm vụ (mặc định sẽ xử lý trong service nếu bỏ trống)
    if model.loai_nhiem_vu:
        _model.loai_nhiem_vu = to_list(model.loai_nhiem_vu)

    # Nhóm nhiệm vụ: chuyển số → La Mã, giữ “I”..“VIII”
    if model.nhom_nhiem_vu:
        raw = to_list(model.nhom_nhiem_vu)
        roman_groups = []
        for x in raw:
            # nếu là số thuần túy
            if re.fullmatch(r"\d+", x):
                roman_groups.append(app.util.utils.int_to_roman_real(int(x)))
            else:
                # bỏ tiền tố "Nhóm" nếu có, rồi giữ nguyên
                txt = x.replace("Nhóm", "").strip()
                if re.fullmatch(r"\d+", txt):
                    roman_groups.append(app.util.utils.int_to_roman_real(int(txt)))
                else:
                    roman_groups.append(txt)
        _model.nhom_nhiem_vu = roman_groups

    # Kỳ báo cáo: nếu có truyền, giữ, nếu không thì để None (service sẽ mặc định today)
    if model.ky_bao_cao_from:
        _model.ky_bao_cao_from = model.ky_bao_cao_from.strip()
    if model.ky_bao_cao_to:
        _model.ky_bao_cao_to = model.ky_bao_cao_to.strip()

    # Ngày hoàn thành: mặc định trong service nếu None
    if model.ngay_hoan_thanh_from:
        _model.ngay_hoan_thanh_from = model.ngay_hoan_thanh_from.strip()
    if model.ngay_hoan_thanh_to:
        _model.ngay_hoan_thanh_to = model.ngay_hoan_thanh_to.strip()
    if hasattr(model, "trang_thai") and model.trang_thai:
        _raw_trang_thai = to_list(model.trang_thai)
        status = []
        for item in _raw_trang_thai:
            key = item.strip().lower()
            if key in status_map:
                status.append(status_map[key])
            else:
                status.append(key)
        _model.trang_thai = status
    # Gọi service xử lý và format kết quả
    return await get_kh02_tracking_results(_model)
