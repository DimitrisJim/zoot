smolregrtest
============

Contains regression tests for the standard library. Basically, this is `libregrtest` from CPython but with
some of the functionality stripped out since it isn't required (detecting refleaks, mp running on tests etc)

The idea here is that we want to run the standard library tests using RustPython. To do this I should probably
fire up a process that spawns a RustPython interpreter and then sends it commands to run the tests. I basically
want `Regrtest`s `good`, `bad` and `skipped` results (and others, probably) in order to annotate the failing
tests with the correct decorator and message. Since the default `libregrtest` just dumps the results to stdout
I could either capture that and parse it or I could have the RustPython interpreter send the results back to
me after altering `libregrtest` to do so. The latter might also involve replacing `libregrtest`'s with `smolregrtest`
before executing.

This is a first idea on how to do it. There might be a simpler way which I am not thinking (running everything with the RustPython interpreter would be one, but I'm not yet confident if it can handle `libcst`).