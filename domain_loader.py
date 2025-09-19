import os
import pandas as pd
from typing import Dict
import logging

logger = logging.getLogger(__name__)

DATA_DIR = os.getenv("DOMAIN_DATA_DIR", "./domain_data")

def _read_xlsx(name: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing data file: {path}")
    return pd.read_excel(path).fillna("")

def load_domain() -> Dict:
    eq = _read_xlsx("equipment_list_minimal.xlsx")         # equipment_name, model_examples (code 컬럼 사용 안 함)
    er = _read_xlsx("error_types_minimal.xlsx")            # error_name,    error_code,   definition, examples
    rq = _read_xlsx("request_type_mapping_minimal.xlsx")   # request_type_label, request_type_code, definition, examples

    # NaN 값 필터링하여 깨끗한 리스트 생성
    allowed = {
        "equipment": [name for name in eq["equipment_name"].tolist() if pd.notna(name) and str(name).strip()],
        "errors":    [code for code in er["error_code"].tolist() if pd.notna(code) and code.strip()],
        "requests":  [code for code in rq["request_type_code"].tolist() if pd.notna(code) and code.strip()],
    }

    # 모델명→장비명 역매핑 생성 (고객이 구체적 모델명 언급 시 사용)
    model_to_equipment = {}
    for _, r in eq.iterrows():
        if pd.notna(r.equipment_name) and pd.notna(r.model_examples) and str(r.model_examples).strip():
            # 세미콜론이나 쉼표로 구분된 모델들 처리
            models = str(r.model_examples).replace(';', ',').split(',')
            for model in models:
                model = model.strip()
                if model:
                    model_to_equipment[model] = r.equipment_name
    
    maps = {
        "equipment_by_name": {r.equipment_name: r.equipment_name for _, r in eq.iterrows() if pd.notna(r.equipment_name)},
        "error_by_name":     {r.error_name: r.error_code for _, r in er.iterrows()},
        "request_by_label":  {r.request_type_label: r.request_type_code for _, r in rq.iterrows()},
        "model_to_equipment": model_to_equipment,  # 모델명→장비명 매핑 추가
    }

    # examples 텍스트→코드 역매핑 생성 (고객 발화 → ERP 코드)
    error_examples_to_code = {}
    for _, r in er.iterrows():
        if pd.notna(r.examples) and pd.notna(r.error_code) and str(r.examples).strip():
            # 세미콜론으로 구분된 예시들 처리
            examples = str(r.examples).split(';')
            for example in examples:
                example = example.strip()
                if example:
                    error_examples_to_code[example] = r.error_code
    
    request_examples_to_code = {}
    for _, r in rq.iterrows():
        if pd.notna(r.examples) and pd.notna(r.request_type_code) and str(r.examples).strip():
            # 세미콜론으로 구분된 예시들 처리
            examples = str(r.examples).split(';')
            for example in examples:
                example = example.strip()
                if example:
                    request_examples_to_code[example] = r.request_type_code
    
    # 매핑에 예시→코드 매핑 추가
    maps["error_examples_to_code"] = error_examples_to_code
    maps["request_examples_to_code"] = request_examples_to_code
    
    # 힌트(프롬프트 tail에 조금만 넣어 환각↓)
    hints = {
        "equipment": [f"{r.equipment_name}: {r.model_examples}" for _, r in eq.iterrows() 
                      if pd.notna(r.model_examples) and str(r.model_examples).strip()],
        "errors":    [f"{r.error_name}({r.error_code}): {r.examples}" for _, r in er.iterrows() 
                      if pd.notna(r.examples) and str(r.examples).strip()],
        "requests":  [f"{r.request_type_label}({r.request_type_code}): {r.examples}" for _, r in rq.iterrows() 
                      if pd.notna(r.examples) and str(r.examples).strip()],
    }

    return {"allowed": allowed, "maps": maps, "hints": hints}
