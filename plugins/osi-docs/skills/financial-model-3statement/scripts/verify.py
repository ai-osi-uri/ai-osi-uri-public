#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify.py — generate_model.py が出力したモデルを検証する。
前提: 先に xlsx スキルの scripts/recalc.py で再計算済み（data_only値が入っている）こと。

  python3 verify.py model.xlsx

出力:
  - 月次/年次 Balance Check（資産−負債−純資産）が全期間0か
  - 月次 連動Check（CF期末−BS現金）が全期間0か
  - 必要資金（無調達トラフ）= MIN(現金残高（増資ゼロ想定））
  - 調達後の最低現金、FY別 売上/営業利益/当期純利益
いずれかのCheckが0でない、または数式エラーがあれば exit code 1。
"""
import sys, openpyxl

def main(path):
    wb=openpyxl.load_workbook(path,data_only=True)
    ok=True
    m=wb['月次三表（FY1-5）']
    MR={(m.cell(row=r,column=1).value or '').strip():r for r in range(1,90)}
    def mrow(label): r=MR[label]; return [m.cell(row=r,column=3+i).value for i in range(60)]
    def num(xs): return [(0 if v is None else v) for v in xs]
    bchk=max(abs(v) for v in num(mrow('Balance Check（資産−負債−純資産=0）')))
    tie =max(abs(v) for v in num(mrow('連動Check（CF期末−BS現金=0）')))
    print(f'月次 Balance Check  max|x| = {bchk}')
    print(f'月次 連動Check      max|x| = {tie}')
    if bchk>1 or tie>1: ok=False
    nf=num(mrow('現金残高（増資ゼロ想定）')); trough=min(nf); ti=nf.index(trough)
    print(f'必要資金（無調達トラフ）= {trough/1e6:,.1f} 百万円 @ 月{ti+1}')
    end=num(mrow('現金期末')); print(f'調達後 最低現金        = {min(end)/1e6:,.1f} 百万円')
    def fysum(label):
        v=num(mrow(label)); return [round(sum(v[k*12:(k+1)*12])/1e6,1) for k in range(5)]
    print('FY 売上(百万)   :',fysum('売上高'))
    print('FY 営業利益(百万):',fysum('営業利益'))
    print('FY 当期純利益   :',fysum('当期純利益'))
    # error scan
    errs=0
    for ws in wb.worksheets:
        for rrow in ws.iter_rows():
            for c in rrow:
                if isinstance(c.value,str) and c.value.startswith('#') and c.value.endswith('!'):
                    errs+=1
    if errs: print('!! 数式エラー検出:',errs); ok=False
    # annual balance check
    y=wb['財務三表（年次・参照）']
    YR={(y.cell(row=r,column=1).value or '').strip():r for r in range(1,80)}
    ab=[y.cell(row=YR['Balance Check（=0）'],column=2+i).value or 0 for i in range(5)]
    print('年次 Balance Check :',[round(v,2) for v in ab])
    if max(abs(v) for v in ab)>1: ok=False
    print('RESULT:', 'OK' if ok else 'NG')
    return 0 if ok else 1

if __name__=='__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv)>1 else 'financial_model.xlsx'))
