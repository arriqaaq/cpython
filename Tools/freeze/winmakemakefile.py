import sys, os, string

# Template used then the program is a GUI program
WINMAINTEMPLATE = """
#include <windows.h>

int WINAPI WinMain(
    HINSTANCE hInstance,      // handle to current instance
    HINSTANCE hPrevInstance,  // handle to previous instance
    LPSTR lpCmdLine,          // pointer to command line
    int nCmdShow              // show state of window
    )
{
    PyImport_FrozenModules = _PyImport_FrozenModules;
    return Py_FrozenMain(__argc, __argv);
}
"""

SERVICETEMPLATE = """
extern int PythonService_main(int, char **);

int main( int argc, char **argv)
{
    PyImport_FrozenModules = _PyImport_FrozenModules;
    return PythonService_main(argc, argv);
}
"""

subsystem_details = {
    # -s flag        : (C entry point template), (is it __main__?), (is it a DLL?)
    'console'        : (None,                    1,                 0),
    'windows'        : (WINMAINTEMPLATE,         1,                 0),
    'service'        : (SERVICETEMPLATE,         0,                 0),
    'com_dll'        : ("",                      0,                 1),
}

def get_custom_entry_point(subsystem):
    try:
        return subsystem_details[subsystem][:2]
    except KeyError:
        raise ValueError, "The subsystem %s is not known" % subsystem


def makemakefile(outfp, vars, files, target):
    save = sys.stdout
    try:
        sys.stdout = outfp
        realwork(vars, files, target)
    finally:
        sys.stdout = save

def realwork(vars, moddefns, target):
    print "# Makefile for Windows (NT or 95) generated by freeze.py script"
    print
    print 'target = %s' % target
    print 'pythonhome = "%s"' % vars['prefix']
    # XXX The following line is fishy and may need manual fixing
    print 'pythonlib = "%s"' % (vars['exec_prefix'] +
                                "/pcbuild/release/python15.lib")

    # We only ever write one "entry point" symbol - either
    # "main" or "WinMain".  Therefore, there is no need to
    # pass a subsystem switch to the linker as it works it
    # out all by itself.  However, the subsystem _does_ determine
    # the file extension and additional linker flags.
    target_link_flags = ""
    target_ext = ".exe"
    if subsystem_details[vars['subsystem']][2]:
        target_link_flags = "-dll"
        target_ext = ".dll"

    print "cdl = /MD" # XXX - Should this come from vars?  User may have specific requirements...
    print
    print "all: $(target)%s" % (target_ext)
    print

    objects = []
    libs = ["shell32.lib", "comdlg32.lib", "wsock32.lib", "user32.lib"]
    for moddefn in moddefns:
        print "# Module", moddefn.name
        for file in moddefn.sourceFiles:
            base = os.path.basename(file)
            base, ext = os.path.splitext(base)
            objects.append(base + ".obj")
            print '%s.obj: "%s"' % (base, file)
            print "\t@$(CC) -c -nologo $(cdl) /D BUILD_FREEZE",
            print "-I$(pythonhome)/Include  -I$(pythonhome)/PC \\"
            print "\t\t$(cflags) $(cdebug) $(cinclude) \\"
            extra = moddefn.GetCompilerOptions()
            if extra:
                print "\t\t%s \\" % (string.join(extra),)
            print '\t\t"%s"' % file
            print

        # Add .lib files this module needs
        for modlib in moddefn.GetLinkerLibs():
            if modlib not in libs:
                libs.append(modlib)

    print "ADDN_LINK_FILES=",
    for addn in vars['addn_link']: print '"%s"' % (addn),
    print ; print

    print "OBJS=",
    for obj in objects: print '"%s"' % (obj),
    print ; print

    print "LIBS=",
    for lib in libs: print '"%s"' % (lib),
    print ; print

    print "$(target)%s: $(OBJS)" % (target_ext)
    print "\tlink -out:$(target)%s %s" % (target_ext, target_link_flags),
    print "\t$(OBJS) \\"
    print "\t$(LIBS) \\"
    print "\t$(ADDN_LINK_FILES) \\"
    print "\t\t$(pythonlib) $(lcustom)\\"
    print "\t\t$(resources)"
    print
    print "clean:"
    print "\t-rm -f *.obj"
    print "\t-rm -f $(target).exe"
