"""Active biochemical fork tests; upstream soft-tech suites are not normative."""
from pathlib import Path
import argparse,json,sys,unittest
GROUPS={
    'biochemical':['test_bio_claims','test_biochemical','test_bio_spacing','test_bio_layout','test_bio_presentation','test_bio_background','test_bio_scripts','test_bio_package'],
    'workflow':['test_three_stage_pools','test_nonblocking_pools','test_cli_evidence','test_incremental_review','test_flat_delivery','test_case_folder_delivery'],
    'pages':['test_render_docx_checked'],
}
def main():
    p=argparse.ArgumentParser();p.add_argument('--group',choices=GROUPS,action='append');p.add_argument('--all',action='store_true');p.add_argument('--list',action='store_true');a=p.parse_args()
    if a.list or not(a.group or a.all):print(json.dumps(GROUPS,ensure_ascii=False,indent=2));return 0
    groups=list(GROUPS) if a.all else a.group;names=list(dict.fromkeys(n for g in groups for n in GROUPS[g]))
    print(json.dumps({'groups':groups,'modules':names,'scope':'Isolated mechanical regressions; zero paid model calls; no production acceptance or throughput claim'},ensure_ascii=False),flush=True)
    suite=unittest.defaultTestLoader.loadTestsFromNames(names);r=unittest.TextTestRunner(verbosity=1).run(suite);return 0 if r.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
