#include <stdio.h>
#include "util.h"
#include "core/model.h"
#include "../include/api.h"
#include "missing.h"
#  include "spaced.h"   // espaco depois do #
#include <util.h>
#define HDR "dead.h"
#include HDR
#ifdef _WIN32
#include "win.h"
#endif
#if 0
#include "dead.h"
#endif
/* #include "ghost.h" */
// #include "ghost.h"
const char *s = "#include \"ghost.h\"";

int main(void) { return 0; }
