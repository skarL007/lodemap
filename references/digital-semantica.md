# Semantic fingerprint per module

`esqueleto.py rascunho` stores a `digital` value for every component in `.lodemap/decisoes-modelo.json`. The value is
`2:` followed by the first 16 hex characters of a sha256 over the module's **public surface**: the parts a one-sentence
description can refer to. When the skeleton is rebuilt, a module with an existing description whose fingerprint changed
is listed in `pendentes.componentes_revisar`, and the modeler revisits only those modules. A module whose code changed
while its fingerprint stayed the same keeps its description. It costs no tokens and needs no agent.

## What counts (version 2)

| Language | Included | Ignored |
|---|---|---|
| Python (`ast`) | module docstring; every top-level `import`; each public top-level function or class with its signature and the first docstring line; public method signatures of each class and its bases; top-level `UPPER_CASE` constants and `__all__`; **names** of public top-level variables; per public class, the names of class attributes, the `__init__` signature, the names of instance attributes assigned in `__init__`, and public nested classes with their public methods | function and method bodies, values, decorators, return annotations, method docstrings, comments, formatting, names starting with `_` |
| JavaScript and TypeScript (text) | the file's leading comment block; top-level declaration and import lines; first-level keys of an exported object literal; `export { }` lists and `export * from`; the full parameter list of an exported function, also when it spans lines; members of an exported class (constructor and method signatures, field names) | bodies, values, JSDoc, inner comments, whitespace inside a declaration, names starting with `_` or `#`, `private` members |
| Go (text) | the file's leading comment block; top-level declaration and import lines; the first line of the doc comment right above an exported `func`, method or `type`, and whether that comment carries `Deprecated:` | bodies, the rest of the doc comment, unexported symbols, `//go:` directives |
| Other languages (text) | the file's leading comment block; declaration and import lines with no indentation (`use`, `package`, `class`, `struct`, `fn`, `const`, and so on); indented `public`, `pub fn` and `protected` lines | bodies, indented code, inner comments |
| Folder module (`dir/`) | the relative path and fingerprint of every file in the folder, sorted | `__pycache__`, `node_modules`, `.git`, `.venv`, `dist`, `build` |

A Python file that does not parse falls back to the text rules.

**Versions.** A fingerprint without the `2:` prefix was written by version 1 (the first three rows without the parts
added above). On the first rebuild after the upgrade the stored value is compared with version 1 of the current code,
so an old map is not sent to review in bulk; the new value is stored and version 2 applies from the next rebuild on.
A decision file older than the fingerprint has no `digital` at all: those modules only get one, none is marked.
Checked on two real maps: axios (72 components) and chi (35) migrated with 0 reviews.

## Measurement

No model is involved: the script reads two releases and compares fingerprints. "Hidden change" is a file version 1 did
not mark although its public surface changed, found by reading every unmarked diff of the first two repositories.

| Repository | Pairs of releases | Files changed | Marked by v1 | Marked by v2 | Hidden changes v1 missed | Caught by v2 | New marks with no surface change |
|---|---|---:|---:|---:|---:|---:|---:|
| [Textualize/rich](https://github.com/Textualize/rich) (Python) | 5, v13.0.0 to v13.9.4 | 78 | 29 | 32 | 3 | 3 | 0 |
| [axios](https://github.com/axios/axios) (JavaScript) | 5, v1.16.0 to v1.21.1 | 100 | 57 | 63 | 9 | 6 | 0 |
| [go-chi/chi](https://github.com/go-chi/chi) (Go) | 8, v5.0.8 to v5.5.0 | 74 | 29 | 32 | not audited | 3 marks added, all 3 real | 0 |

- rich: the three were an instance attribute and an `__init__` parameter (`logging.py`), class attributes (`tree.py`)
  and an instance attribute (`spinner.py`). With version 2, 59% of the changed files skip review (it was 63%).
- axios: the six were option keys of exported objects and multi-line signatures (`transitional.js`,
  `HttpStatusCode.js`, `progressEventReducer.js`). The three still missed are an option key read inside a function
  body (`Axios.js` twice, `mergeConfig.js`): no rule on names can see them.
- chi: version 1 read only the top of the file, and in Go the documentation sits above each function. In v5.5.0
  `middleware.Sunset` stopped writing the `Deprecation` header (a new `Deprecation` middleware took it over) with the
  same signature; only the doc comment said so, and the stored description became false without a review. The Go rule
  marks it. The other two marks it adds over eight releases are `Mux.Group` (a "fresh" middleware stack became "a
  copy") and `RealIP` being deprecated. The unmarked chi diffs were not read one by one.
- Mutations (one change applied to every file of a release where it fits, 78 rich files and 72 axios files): of the
  changes that should mark a file, version 2 closes `__init__` parameters (42 of 42 files), public variables (78 of
  78), class attributes (57 of 57) and nested classes (57 of 57) in Python, and in JavaScript keys of a default-export
  object (8 of 8), export lists (1 of 1), class fields (10 of 10), class methods (10 of 11) and constructor parameters
  (9 of 10); whitespace inside a JavaScript declaration no longer marks a file (37 false marks became 0). No mutation
  that should leave the fingerprint alone started to change it. Left open on purpose: method docstrings, decorators,
  return annotations and JSDoc. Left open by design: assignment to a property of an exported name outside its literal
  (`Name.x = ...`, 61 of 61 files), a function exported only through an alias, and renaming a top-level function that
  is not exported, which still marks the file (23 of 24, inherited from version 1).
- While measuring, a defect of the shared JavaScript tokenizer showed up: a quote inside a regular expression literal
  opened a "string" that swallowed the rest of the file (the class in `AxiosHeaders.js` was invisible). The masker now
  recognizes a regex by what precedes it.

Rebuilding every description at each of the five rich releases would mean 390 descriptions.

## Limits

- A change of behavior that leaves the public surface untouched, such as a function that keeps its signature and
  documentation but does something else, does not trigger a review. In the two audited repositories that was 3 of the
  178 changed files after version 2. The quality gate and the next full regeneration remain the safety net.
- The audit of unmarked files was done by reading diffs, by one reader, on two repositories.
- The text rules are line patterns, not a parser. Rust, Java, Kotlin, C# and C/C++ keep the version 1 rules and have no
  measurement on a real repository. In JavaScript, JSDoc does not count, so a behavior change documented only there is
  missed; in Go only the first doc line counts.
