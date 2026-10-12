import os

# sklearn pulls in joblib/loky, which shells out to `sysctl` to count physical
# cores on macOS. When this package is imported from an environment whose PATH
# lacks /usr/sbin (its standard location), that probe fails with a UserWarning
# and loky silently falls back to the logical core count. Ensuring /usr/sbin is
# on PATH lets the real probe succeed; harmless on Linux, where loky reads
# /proc instead. Must run before the first `from sklearn ...` import below.
if "/usr/sbin" not in os.environ.get("PATH", "").split(os.pathsep):
    os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + "/usr/sbin"
