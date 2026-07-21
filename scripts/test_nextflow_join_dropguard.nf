#!/usr/bin/env nextflow
// Regression test for #60 — the matrix<->best_subset pairing must NEVER drop an evaluator.
//
// It reproduces the exact operator chain from workflows/kreview_eval.nf (Step 4b/4c): three
// evaluator matrices, but only two best_subset files — the third (WPS) is missing, exactly as
// happens when an evaluator's ablation fails and is ignored upstream. The fixed chain uses
// join(remainder:true) + a NO_BEST_SUBSET fallback, so all three survive; the old combine(by:0)
// inner-join would silently drop WPS. Asserts both survival and the correct fallback.
//
// Run:  nextflow run scripts/test_nextflow_join_dropguard.nf
// Exit: 0 = no drop, non-zero = an evaluator was dropped or mis-paired.

nextflow.enable.dsl = 2

workflow {
    // 3 matrices, 2 subsets (WPS's best_subset is absent — the #60 trigger).
    matrices = Channel.of('ATAC', 'FSC', 'WPS').map { [it, file("${it}_matrix.parquet")] }
    subsets  = Channel.of('ATAC', 'FSC').map { [it, file("${it}_best_subset.json")] }

    // --- exact chain from kreview_eval.nf Step 4b (keep in sync with the source) ---
    paired = matrices
        .join(subsets, by: 0, remainder: true)
        .filter { it[1] != null }
        .map { key, matrix, bs ->
            if (bs == null) {
                log.warn "[#60-test] best_subset MISSING for '${key}' — fallback to NO_BEST_SUBSET"
            }
            [key, (bs ?: file('NO_BEST_SUBSET')).name]
        }

    paired.collect(flat: false).view { rows ->
        assert rows.size() == 3 :
            "DROP BUG (#60): expected 3 evaluators, got ${rows.size()}: ${rows}"
        def keys = rows.collect { it[0] }.sort()
        assert keys == ['ATAC', 'FSC', 'WPS'] :
            "DROP BUG (#60): evaluator set changed — got ${keys}"
        def wps = rows.find { it[0] == 'WPS' }
        assert wps[1] == 'NO_BEST_SUBSET' :
            "FALLBACK BUG (#60): WPS should pair with NO_BEST_SUBSET, got '${wps[1]}'"
        def atac = rows.find { it[0] == 'ATAC' }
        assert atac[1] == 'ATAC_best_subset.json' :
            "PAIRING BUG (#60): ATAC mis-paired with '${atac[1]}'"
        return "PASS (#60): 3 evaluators kept; WPS fell back to NO_BEST_SUBSET; ATAC paired correctly"
    }
}
