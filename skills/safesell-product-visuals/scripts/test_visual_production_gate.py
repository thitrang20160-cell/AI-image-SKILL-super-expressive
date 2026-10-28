"""Isolated synthetic offline tests; no image model, accounts, network or paid checks."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from visual_production_gate import evaluate, digest


def save(path, obj):
    Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')


def ref(path):
    return {'file':str(Path(path).resolve()),'sha256':digest(path)}


def fixture_png():
    def chunk(tag,data):
        return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00\x11\x22\x33'))+chunk(b'IEND',b'')


def make_fixture(base, sku='TEST-001', purpose='feature', slot_role='feature-1'):
    base=Path(base).resolve();base.mkdir(parents=True,exist_ok=True)
    product=base/'synthetic-product.png';product.write_bytes(fixture_png())
    style=base/'synthetic-style.png';style.write_bytes(fixture_png())
    output=base/'synthetic-output.png';output.write_bytes(fixture_png())
    approval=base/'synthetic-approval.txt';approval.write_text('Synthetic fixture only; not real user approval.',encoding='utf-8')
    locked=purpose not in ('master','dimensions')
    brief={'sku':sku,'image_type':purpose,'visual_production':{'version':1},'realism':{'mode':'grounded-advertising'},'review_set':False,
           'style_lock':{'required':locked,'reason':'Platform main image / factual dimension branch' if not locked else None,'transfer':['near/middle/far product hierarchy'],'exclude':['source brand and claims']},
           'composition':{'action':'use' if locked else 'display','near':'product','middle':'contact and type','far':'context','tension_source':'scale and depth','primary_subject':'product'},
           'spatial_type':{'enabled':locked},'effects':{'enabled':False},'material_expression':{'enabled':purpose=='material','action':'contact','visual_result':'material contrast'},'message':{'exact_copy':['TEST COPY']}}
    brief_file=base/'brief.json';save(brief_file,brief)
    inputs=[dict(ref(product),role='product-identity')]
    attached=[str(product)]
    if locked:
        inputs.append(dict(ref(style),role='style-reference',approval={'status':'user-approved-style','evidence':ref(approval)}));attached.append(str(style))
    request={'schema_version':1,'sku':sku,'purpose':purpose,'slot_role':slot_role,'mode':'generate','tool':'built-in image_gen','brief':ref(brief_file),'inputs':inputs,'tool_args':{'prompt':'Synthetic fixture, not a production request.','referenced_image_paths':attached,'transparent_background':False}}
    request_file=base/'request.json';save(request_file,request)
    keys=['product_identity','copy_and_claims','style_match','product_priority','purpose_expression','material_scale','contact_and_operation','spatial_type','effects','set_consistency','physical_plausibility']
    if purpose=='material':keys+=['material_event','material_tension']
    review={'schema_version':1,'review_id':'synthetic-review','sku':sku,'purpose':purpose,'brief':ref(brief_file),'generation_request':ref(request_file),'output':ref(output),'reviewer':{'kind':'creator-self-check','independent_context':False},
            'checks':{k:{'status':'pass','evidence':'Synthetic fixture only; no actual image review.'} for k in keys},'judgment':'pass','unresolved_defects':[],
            'inspection':{'full_size':True,'thumbnail':True,'evidence':'Synthetic fixture inspection flags; not actual vision.'},'observed_copy':['TEST COPY'],
            'comparisons':[{'reference':ref(style),'evidence':'Synthetic comparison fixture only.'}] if locked else [],'user_style_approval':None}
    review_file=base/'review.json';save(review_file,review)
    return {'base':base,'product':product,'style':style,'output':output,'approval':approval,'brief_file':brief_file,'request_file':request_file,'review_file':review_file,'brief':brief,'request':request,'review':review}


class GateTests(unittest.TestCase):
    workdir=None
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='visual-gate-',dir=self.workdir)
        self.f=make_fixture(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def run_gate(self,request=None,review=None,with_review=True):
        if request is not None:save(self.f['request_file'],request)
        if review is not None:save(self.f['review_file'],review)
        return evaluate(self.f['request_file'],self.f['review_file'] if with_review else None)
    def v2_fixture(self, purpose='feature', slot_role='feature-1'):
        f=make_fixture(self.f['base']/('v2-'+purpose),purpose=purpose,slot_role=slot_role)
        f['brief']['visual_production']['version']=2
        f['brief']['non_text_visual_tension']={
            'event':{'product_part':'actual zipper','physical_action_or_relation':'hand opens zipper','visible_result':'opening reveals product interior'},
            'camera_choice':'low close three-quarter view',
            'light_or_material_choice':'side light reveals folds',
            'first_read_without_words':'diagonal contact and opened pouch',
            'visual_levers':['action','geometry','material'],
            'typography_role':'supporting'}
        save(f['brief_file'],f['brief']);f['request']['brief']=ref(f['brief_file']);save(f['request_file'],f['request'])
        f['review']['brief']=ref(f['brief_file']);f['review']['generation_request']=ref(f['request_file'])
        f['review']['checks']['non_text_tension']={'status':'pass','evidence':'Synthetic fixture only; image judgment unproven.'}
        f['review']['non_text_visual_review']={'status':'pass','product_first_read':'synthetic green pouch',
            'visible_cause':'synthetic hand at zipper','visible_result':'synthetic open panel',
            'eye_path_without_words':'product then zipper then opening','why_typography_is_secondary':'synthetic text is not the mechanism'}
        save(f['review_file'],f['review'])
        return f
    def test_valid_input_and_record(self):
        self.assertTrue(self.run_gate(with_review=False)['ok'])
        self.assertTrue(self.run_gate()['ok'])
    def test_missing_and_unattached_references(self):
        for role in ('product-identity','style-reference'):
            with self.subTest(role=role):
                request=copy.deepcopy(self.f['request'])
                remove=[r['file'] for r in request['inputs'] if r['role']==role]
                request['inputs']=[r for r in request['inputs'] if r['role']!=role]
                request['tool_args']['referenced_image_paths']=[p for p in request['tool_args']['referenced_image_paths'] if p not in remove]
                self.assertFalse(self.run_gate(request=request,with_review=False)['ok'])
        request=copy.deepcopy(self.f['request']);request['tool_args']['referenced_image_paths'].pop()
        self.assertFalse(self.run_gate(request=request,with_review=False)['ok'])
    def test_changed_anchor_is_blocked(self):
        self.f['style'].write_bytes(b'changed')
        self.assertFalse(self.run_gate()['ok'])
    def test_generated_draft_not_promoted_to_anchor(self):
        request=copy.deepcopy(self.f['request']);request['inputs'][1]['approval']['status']='unapproved-draft'
        self.assertFalse(self.run_gate(request=request,with_review=False)['ok'])
    def test_seed_not_exposed_by_tool(self):
        request=copy.deepcopy(self.f['request']);request['tool_args']['seed']=42
        self.assertFalse(self.run_gate(request=request,with_review=False)['ok'])
    def test_current_tool_accepts_five_reference_images_but_not_six(self):
        request=copy.deepcopy(self.f['request'])
        for index in range(3):
            extra=self.f['base']/('extra-draft-'+str(index)+'.png')
            extra.write_bytes(fixture_png())
            request['inputs'].append(dict(ref(extra),role='draft'))
            request['tool_args']['referenced_image_paths'].append(str(extra))
        self.assertTrue(self.run_gate(request=request,with_review=False)['ok'])
        extra=self.f['base']/'sixth-draft.png';extra.write_bytes(fixture_png())
        request['inputs'].append(dict(ref(extra),role='draft'))
        request['tool_args']['referenced_image_paths'].append(str(extra))
        result=self.run_gate(request=request,with_review=False)
        self.assertIn('reference_images_exceed_current_tool_limit_five',result['errors'])
    def test_edit_needs_target_and_original_inputs(self):
        request=copy.deepcopy(self.f['request']);request['mode']='edit'
        self.assertFalse(self.run_gate(request=request,with_review=False)['ok'])
        target=self.f['base']/'edit-target.png';target.write_bytes(fixture_png())
        request['inputs'].append(dict(ref(target),role='draft'));request['tool_args']['referenced_image_paths'].append(str(target))
        self.assertTrue(self.run_gate(request=request,with_review=False)['ok'])
    def test_scope_cannot_be_reused_for_another_sku_or_slot(self):
        self.assertFalse(evaluate(self.f['request_file'],self.f['review_file'],expected_sku='OTHER')['ok'])
        self.assertFalse(evaluate(self.f['request_file'],self.f['review_file'],expected_role='feature-2')['ok'])
    def test_no_composition_contract(self):
        brief=copy.deepcopy(self.f['brief']);del brief['composition']['near'];save(self.f['brief_file'],brief)
        request=copy.deepcopy(self.f['request']);request['brief']=ref(self.f['brief_file'])
        self.assertFalse(self.run_gate(request=request,with_review=False)['ok'])
    def test_review_is_bound_to_request_bytes(self):
        request=copy.deepcopy(self.f['request']);request['tool_args']['prompt']='Changed after review'
        self.assertFalse(self.run_gate(request=request)['ok'])
    def test_review_is_bound_to_output_bytes(self):
        self.f['output'].write_bytes(b'changed output')
        self.assertFalse(self.run_gate()['ok'])
    def test_unknown_or_failed_style_blocks_overall_pass(self):
        for status in ('unknown','fail'):
            with self.subTest(status=status):
                review=copy.deepcopy(self.f['review']);review['checks']['style_match']['status']=status
                self.assertFalse(self.run_gate(review=review)['ok'])
    def test_wrong_text_or_unresolved_defect_blocks_release(self):
        review=copy.deepcopy(self.f['review']);review['observed_copy']=['WRONG COPY']
        self.assertFalse(self.run_gate(review=review)['ok'])
        review=copy.deepcopy(self.f['review']);review['unresolved_defects']=['Obscured letter']
        self.assertFalse(self.run_gate(review=review)['ok'])
    def test_self_check_is_never_independent(self):
        review=copy.deepcopy(self.f['review']);review['reviewer']['independent_context']=True
        self.assertFalse(self.run_gate(review=review)['ok'])
    def test_full_size_and_thumbnail_and_comparison_required(self):
        for field in ('full_size','thumbnail'):
            review=copy.deepcopy(self.f['review']);review['inspection'][field]=False
            self.assertFalse(self.run_gate(review=review)['ok'])
        review=copy.deepcopy(self.f['review']);review['comparisons']=[]
        self.assertFalse(self.run_gate(review=review)['ok'])
    def test_material_event_and_tension_are_required(self):
        material=make_fixture(self.f['base']/'material',purpose='material',slot_role='material')
        self.assertTrue(evaluate(material['request_file'],material['review_file'])['ok'])
        material['review']['checks']['material_tension']['status']='unknown';save(material['review_file'],material['review'])
        self.assertFalse(evaluate(material['request_file'],material['review_file'])['ok'])
        material['brief']['material_expression']['enabled']=False;save(material['brief_file'],material['brief'])
        material['request']['brief']=ref(material['brief_file']);save(material['request_file'],material['request'])
        self.assertFalse(evaluate(material['request_file'])['ok'])
    def test_v2_requires_physical_visual_plan_before_generation(self):
        f=self.v2_fixture()
        self.assertTrue(evaluate(f['request_file'])['ok'])
        cases=[
            ('no_plan',lambda b:b.pop('non_text_visual_tension')),
            ('no_result',lambda b:b['non_text_visual_tension']['event'].pop('visible_result')),
            ('only_type',lambda b:b['non_text_visual_tension'].update({'typography_role':'primary'})),
            ('one_lever',lambda b:b['non_text_visual_tension'].update({'visual_levers':['action']})),
        ]
        original=copy.deepcopy(f['brief'])
        for label,mutate in cases:
            with self.subTest(case=label):
                broken=copy.deepcopy(original);mutate(broken);save(f['brief_file'],broken)
                request=copy.deepcopy(f['request']);request['brief']=ref(f['brief_file']);save(f['request_file'],request)
                self.assertFalse(evaluate(f['request_file'])['ok'])
    def test_v2_requires_observed_visual_without_typography_after_generation(self):
        f=self.v2_fixture()
        self.assertTrue(evaluate(f['request_file'],f['review_file'])['ok'])
        original=copy.deepcopy(f['review'])
        cases=[
            ('missing_review',lambda r:r.pop('non_text_visual_review')),
            ('unknown',lambda r:r['non_text_visual_review'].update({'status':'unknown'})),
            ('no_eye_path',lambda r:r['non_text_visual_review'].pop('eye_path_without_words')),
            ('failed_check',lambda r:r['checks']['non_text_tension'].update({'status':'fail'})),
            ('missing_check',lambda r:r['checks'].pop('non_text_tension')),
        ]
        for label,mutate in cases:
            with self.subTest(case=label):
                broken=copy.deepcopy(original);mutate(broken);save(f['review_file'],broken)
                self.assertFalse(evaluate(f['request_file'],f['review_file'])['ok'])
    def test_v2_material_retains_material_event_and_non_text_tension(self):
        f=self.v2_fixture('material','material')
        self.assertTrue(evaluate(f['request_file'],f['review_file'])['ok'])
        broken=copy.deepcopy(f['review']);broken['checks']['material_tension']['status']='unknown'
        save(f['review_file'],broken)
        self.assertFalse(evaluate(f['request_file'],f['review_file'])['ok'])
    def test_platform_main_image_does_not_require_advertising_type(self):
        main=make_fixture(self.f['base']/'master',purpose='master',slot_role='master')
        self.assertTrue(evaluate(main['request_file'],main['review_file'])['ok'])
    def test_malformed_records_fail_closed(self):
        for value in ([],{},True,'wrong'):
            save(self.f['request_file'],value)
            self.assertFalse(evaluate(self.f['request_file'])['ok'])

    def test_delivery_gate_runs_live_visual_contract(self):
        from png_provenance_export import export_copy
        from detect_image_signals import summarize
        from delivery_gate import evaluate as deliver
        final=self.f['base']/'export.png';metadata=self.f['base']/'metadata.json'
        save(metadata,export_copy(self.f['output'],final,'preserve'))
        sha=digest(final)
        rows={name:{'kind':'pixel_watermark','check_status':'not_performed','outcome':'unknown','checked_sha256':sha} for name in ('openai_synthid','trustmark_qp')}
        coverage=self.f['base']/'coverage.json';save(coverage,{'file':str(final),'sha256':sha,'detectors':rows,'summary':summarize(rows)})
        missing_pixel=self.f['base']/'not-run.json'
        kwargs={'metadata_policy':'preserve','accept_pixel_limitations':True,'coverage_path':coverage}
        good=deliver(final,self.f['review_file'],metadata,missing_pixel,generation_request=self.f['request_file'],**kwargs)
        self.assertTrue(good['requirements_met'],good)
        missing=deliver(final,self.f['review_file'],metadata,missing_pixel,**kwargs)
        self.assertIn('generation_request_missing_for_new_visual_contract',missing['reasons'])
        review=copy.deepcopy(self.f['review']);review['comparisons']=[];save(self.f['review_file'],review)
        bad=deliver(final,self.f['review_file'],metadata,missing_pixel,generation_request=self.f['request_file'],**kwargs)
        self.assertIn('visual_production_evidence_incomplete_or_stale',bad['reasons'])

    def test_ambiguous_metadata_marker_remains_blocked(self):
        from png_provenance_export import export_copy
        from delivery_gate import evaluate as deliver
        raw=self.f['output'].read_bytes();tag=b'caBX';payload=b'c2pa-without-required-terminator'
        chunk=struct.pack('>I',len(payload))+tag+payload+struct.pack('>I',zlib.crc32(tag+payload)&0xffffffff)
        self.f['output'].write_bytes(raw[:-12]+chunk+raw[-12:])
        final=self.f['base']/'ambiguous-export.png';metadata=self.f['base']/'ambiguous-metadata.json'
        record=export_copy(self.f['output'],final,'remove-c2pa');save(metadata,record)
        self.assertEqual(record['metadata_status'],'needs-review')
        result=deliver(final,self.f['review_file'],metadata,self.f['base']/'not-run.json',accept_pixel_limitations=True,generation_request=self.f['request_file'])
        self.assertFalse(result['requirements_met'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workdir',type=Path,required=True)
    args=parser.parse_args();base=args.workdir.resolve()
    if base.drive.upper()=='C:':parser.error('Use an isolated directory on I:')
    base.mkdir(parents=True,exist_ok=True);GateTests.workdir=base
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(GateTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    save(base/'visual-gate-regression.json',{'kind':'synthetic-offline-only','tests_run':result.testsRun,'passed':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),'noNetworkOrPaidGeneration':True,'noActualImageApproval':True})
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__=='__main__':main()
