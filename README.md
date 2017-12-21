# asap-graph

This is one of my first programming projects so you may find some ugly hacks and hardcoded stuff. Hopefuly will get some time to fix it some day :)

asap-graph is a sar graphing tool using matplotlib capable of plotting a single file, an interval of files, or go recursively through a folder, i.e. sosreport folder. It was designed as a better way to plot and inspect sar data, as it creates a single PNG file with the following data: %CPU, memory, swap, load, plist, runq, proc/s, cswch/s and network sockets. It works with any sar files from RHEL5, 6 and 7 and it handles all differences between those versions automatically.
