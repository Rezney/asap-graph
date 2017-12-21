#!/usr/bin/python3

"""
Usage: asap-graph file [-aoclmsb] (FILE) [FILE]... [ -p SAVEPATH] 
       asap-graph cat [-aoclmsb] (FILE) (FILE) [-p SAVEPATH]
       asap-graph xp [-aoclmsb] [-p SAVEPATH] [-x XPATH]
        
    Modes:
          
          file          Provide one sar file to plot. 
          cat           Concatenate sar files together.
          xp            Extract sar files recursively and plot it.
    
    Arguments:
          
          FILE          Mandatory sar file / two sar files as range for concatenation.
              
    Options:
          
          -h --help
          -a            All graphs switched on.
          -o            Overview graphs.
          -c            CPU graphs.
          -l            Load graphs.
          -m            Memory graphs.
          -s            Miscellaneous graphs.
          -b            Storage (block) graphs.
          -p SAVEPATH   Provide save path.
          -x XPATH      Optional path when extracting recursively (Default: cwd).
"""

import warnings
warnings.filterwarnings("ignore")
import re
import os
import sys
import shutil
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.pylab as pylab
import datetime
import time
import numpy as np
import numpy.ma as ma 
from docopt import docopt


def list_get(lst, index, default = None): # returns list index (time only)
    if len(lst) >= index + 1:
        return lst[index]
        
    return default
                    
def complete_concat_sars(concat_sars): # complete sarfiles for concatenation
    
    try:
        from_path_prefix = re.search('(.*)(?=sar)', "".join(concat_sars[0])).group(0)
        to_path_prefix = re.search('(.*)(?=sar)', "".join(concat_sars[1])).group(0)
        
        sar_from = int(re.search('(?<=sar)(\d+)', "".join(concat_sars[0])).group(1))
        sar_to = int(re.search('(?<=sar)(\d+)', "".join(concat_sars[1])).group(1))
        
        sarfiles_filled = []
        
        if from_path_prefix == to_path_prefix:
            if sar_from <= sar_to:                
                for suffix in range(sar_from, sar_to + 1):
                    if len(str(suffix)) == 1:
                        sarfiles_filled.append(from_path_prefix + "sar0" + str(suffix))
                    else:
                        sarfiles_filled.append(from_path_prefix + "sar" + str(suffix))
                
            else:
                for suffix in range(sar_from, 32):
                    if len(str(suffix)) == 1:
                        sarfiles_filled.append(from_path_prefix + "sar0" + str(suffix))
                    else:
                        sarfiles_filled.append(from_path_prefix + "sar" + str(suffix))
                for suffix in range(1, sar_to + 1):
                    if len(str(suffix)) == 1:
                        sarfiles_filled.append(from_path_prefix + "sar0" + str(suffix))
                    else:
                        sarfiles_filled.append(from_path_prefix + "sar" + str(suffix))
    
            return sarfiles_filled
    
        else:
            print(Bcolors.FAIL + ("Different paths for concatenation") + Bcolors.ENDC)
            exit(1)

    except AttributeError:
        print(Bcolors.FAIL + ("Is provided file a valid sar file?") + Bcolors.ENDC)
        exit(1)

class Bcolors: # just class for colors
    FAIL = '\033[91m'
    ENDC = '\033[0m'

class SARAnalyzer:
        
    def __init__(self):
        self.data = {} # main data dict
        self.hostname = ''
        self.cpu_num = ''
    
        # list of used titles
        self.indeces = {'%usr': None, '%user': None, '%nice': None, '%sys': None, '%system': None, '%idle': None, '%iowait': None, 
                    'cswch/s': None, 'proc/s': None, 
                    'ldavg-1': None, 'ldavg-5': None, 'ldavg-15': None, 'runq-sz': None, 'plist-sz': None,
                    'kbmemfree': None, 'kbmemused': None, 'kbcached': None, 'kbswpfree': None, 'kbswpused': None,
                    'pswpin/s': None, 'pswpout/s': None,
                    'dentunusd': None, 'file-nr': None, 'inode-nr': None, 'file-sz': None, 'inode-sz': None,
                    'tcpsck': None, 'udpsck': None,
                    'bread/s': None, 'bwrtn/s': None}
    
    def get_sars_recursively(self, wd = os.getcwd()):
     
        sar_files_list = []
                           
        for root, dirs, files in os.walk(wd):            
            for sarfiles in files:

                sarfile = re.match('sar\d{2}$', sarfiles) 
                                        
                if sarfile:
                    file_with_path = os.path.join(os.path.abspath(root), sarfiles)
                    sar_files_list.append(file_with_path)
                    
        return sar_files_list
    
    def return_indeces(self, row): 
        
        temp_dict = {}
        for index in self.indeces:
            for num, dat in enumerate(row):
                if dat in index:
                    temp_dict.update({dat: num})
                    
        return temp_dict
       
    def get_data(self, sarfile):
        
        print('Processing "%s"...' % sarfile)
                               
        cpu_captured = []
        procs_captured = []
        cswch_captured = []
               
        load_captured = []
        
        mem_captured = []
        swp_captured = []
        
        pswp_captured = []
        
        misc_captured = []
        sck_captured = []
        
        blocks_captured = []
        
        restarts = []
        graphdate = ''
      
        try:
            with open(sarfile, "r") as data:
                        
                state = "default" # state for not capturing 
                
                first_line = data.readline().rstrip() # check first line to determine for RHEL version we are working with (means different sar)
                                
                commas = re.compile("(?<=\d),(?=\d)") # workaround to deal with different locales (e.g. comma instead of dot)
                
                self.hostname = re.search(r"\((.*?)\)", first_line).group(1) 
                
                if re.search('(2.6.18)', first_line):
                    self.rhel_version = 5
                elif re.search('(2.6.32)', first_line):
                    self.rhel_version = 6
                elif re.search('(3.10)', first_line):
                    self.rhel_version = 7
                else:
                    print(Bcolors.FAIL + ("FAIL: Unsupported RHEL/kernel") + Bcolors.ENDC)
                    return
                
                try:
                    self.cpu_num = re.search(r"\((\d+ CPU)\)$", first_line).group(1)
                except AttributeError:
                    self.cpu_num = ""
                       
                graphdateparts = re.search('(?<=\s)(?:(\d+)([-/])(\d+)[-/](\d+))', first_line).groups() # 
                
                # Normalize graphdate

                # year(four digits)-month-day
                if graphdateparts[1] == "-":
                    graphdate = "%s-%s-%s" % (graphdateparts[0][-2:], graphdateparts[2], graphdateparts[3])
                # month-day-year(two digits)
                elif graphdateparts[1] == "/" and len(graphdateparts[3]) == 2:
                    graphdate = "%s-%s-%s" % (graphdateparts[3], graphdateparts[0], graphdateparts[2])
                # month-day-year(four digits)    
                elif graphdateparts[1] == "/" and len(graphdateparts[3]) == 4:
                    graphdate = "%s-%s-%s" % (graphdateparts[3][-2:], graphdateparts[0], graphdateparts[2])
                else:
                    raise LookupError("Unknown graph date format: %s" % str(graphdateparts))
                
                for line in data:                    
                    if line == '\n':
                        continue                        
                    else:
                        commarow = commas.sub('.', line) # implementing the comma workaround

                        row = commarow.split() 
                        am_pm = list_get(row, 1)
                        locale = ['Average:', 'Среднее:', 'Media:', 'Média:', 'Moyenne:', 'Durchschn.:']
                        if am_pm in ("PM", "AM"):
                            t_split = row[0].split(":",1)
                            h = t_split[0]
                            if am_pm == "PM" and t_split[0] != "12":
                                h = (int(t_split[0])+12)
                            if am_pm == "AM" and t_split[0] == "12":
                                h = "00"
                            row[0] = "%s:%s" % (h, t_split[1])
                            del(row[1]) # fixes the BUG with concatenation where there is both non-AM_PM and AM_PM timing.

                        if state == "default":
                            if any(x in row for x in ["%usr", "%user"]):
                                state = "cpu_capturing"
                                self.indeces.update(self.return_indeces(row))                   
                            elif self.rhel_version == 5 and "cswch/s" in row:
                                state = "cswch_capturing"
                                self.indeces.update(self.return_indeces(row))
                            elif self.rhel_version == 5 and "proc/s" in row:
                                state = "procs_capturing"
                                self.indeces.update(self.return_indeces(row))
                            elif all(x in row for x in ["cswch/s", "proc/s"]):                   
                                state = "procs_cswch_capturing"
                                self.indeces.update(self.return_indeces(row))
                            elif "pswpin/s" in row:
                                state = "pswp_capturing"
                                self.indeces.update(self.return_indeces(row))
                            elif "ldavg-15" in row:
                                state = "load_capturing"
                                self.indeces.update(self.return_indeces(row))
                            elif "kbmemfree" in row:
                                state = "mem_capturing" 
                                self.indeces.update(self.return_indeces(row))        
                            elif self.rhel_version in (6, 7) and "kbswpfree" in row:
                                state = "swp_capturing"
                                self.indeces.update(self.return_indeces(row))
                            elif self.rhel_version == 5 and "kbswpfree" in row:
                                state = "swp_rhel5_capturing" # finish    
                            elif "dentunusd" in row:
                                state = "dent_capturing"
                                self.indeces.update(self.return_indeces(row))
                            elif "tcpsck" in row:
                                state = "sck_capturing"
                                self.indeces.update(self.return_indeces(row))
                            elif "bread/s" in row:
                                state = "blocks_capturing"
                                self.indeces.update(self.return_indeces(row))     
                            elif all(x in row for x in ["LINUX", "RESTART"]):
                                restarts.append(row[0])
                                
                            
                        elif state == "cpu_capturing":
                            if any(x in row for x in locale):
                                state = "default"
                            elif "all" in row:
                                cpu_captured.append(row) 
                        elif state == "cswch_capturing":
                            if any(x in row for x in locale):
                                state = "default"
                            else:
                                cswch_captured.append(row) 
                        elif state == "procs_capturing":
                            if any(x in row for x in locale):
                                state = "default"
                            else:                      
                                procs_captured.append(row) 
                        elif state == "procs_cswch_capturing":
                            if any(x in row for x in locale):
                                state = "default"
                            else:                      
                                procs_captured.append(row) 
                                cswch_captured.append(row) 
                        elif state == "pswp_capturing":
                            if any(x in row for x in locale):
                                state = "default"
                            else:
                                pswp_captured.append(row) 
                        elif state == "load_capturing":
                            if any(x in row for x in locale):
                                state = "default"
                            else:
                                load_captured.append(row) 
                        elif state == "mem_capturing":
                            if any(x in row for x in locale):
                                state = "default"
                            else:
                                mem_captured.append(row) 
                        elif state == "swp_rhel5_capturing":
                            if any(x in row for x in locale):
                                state = "default"
                            else:       
                                swp_captured.append(row)
                        elif state == "swp_capturing":
                            if any(x in row for x in locale):
                                state = "default"
                            else:
                                swp_captured.append(row)
                        elif state == "dent_capturing":
                            if any(x in row for x in locale):
                                state = "default"
                            else:
                                misc_captured.append(row) 
                        elif state == "sck_capturing":
                            if any(x in row for x in locale):
                                state = "default"
                            else:
                                sck_captured.append(row)
                        elif state == "blocks_capturing":
                            if any(x in row for x in locale):
                                state = "default"
                            else:
                                blocks_captured.append(row)
                        

                        
                # Dict of dicts of our data (graphdate for contacanation)
                self.data[graphdate] = {
                                        
                    "cpu_captured": cpu_captured,
                    "procs_captured": procs_captured,
                    "cswch_captured": cswch_captured,                    
                    "load_captured": load_captured,                    
                    "mem_captured": mem_captured,                    
                    "swp_captured": swp_captured,                    
                    "pswp_captured": pswp_captured,                    
                    "misc_captured": misc_captured,                    
                    "sck_captured": sck_captured,
                    "blocks_captured": blocks_captured,                    
                    "restarts": restarts,
                    
                }
        except ValueError:
            print(Bcolors.FAIL + ("FAIL: Error capturing %s data!" % sarfile) + Bcolors.ENDC)  
            return
            
        except FileNotFoundError:
            print(Bcolors.FAIL + ("FAIL: %s not found!" % sarfile) + Bcolors.ENDC)
            return
        
        except AttributeError:
            print(Bcolors.FAIL + ("FAIL: Check %s validity" % sarfile) + Bcolors.ENDC)
            return
        
        except PermissionError:
            print(Bcolors.FAIL + ("FAIL: Permission denied!") + Bcolors.ENDC)
        
    # Method for generating the graphs
                
    def generate_graphs(self, file_prefix = None,
                    plot_all = False,
                    plot_overview = True,
                    plot_cpu = False,
                    plot_load = False,
                    plot_memory = False,
                    plot_misc = False,
                    plot_blocks = False, 
                    save_path = None
    ):              
        
        if plot_all == True:
            plot_overview = True
            plot_cpu = True
            plot_load = True
            plot_memory = True
            plot_misc = True
            plot_blocks = True
        
        default = [plot_all, plot_overview, plot_cpu, plot_load, plot_memory, plot_misc, plot_blocks] # complicated as was not able to find default for 'docopt'
        
        if not any(default):
            plot_overview = True
                       
        if not file_prefix:
            ks = sorted(self.data.keys()) # sorted keys (graph dates)
            if not ks:
                return

            file_suffix = (ks[0] + "_to_" + ks[-1]) if ks[0] != ks[-1] else ks[0] # generate file prefix (from graphdates)
            file_prefix = self.hostname + "__"  
            save_name = save_path + "/" + file_prefix + file_suffix if save_path != None else file_prefix + file_suffix
    
        # variables init as extend used later
        
        restarttime = []
        
        cputime = []
        user = []
        nice = []
        system = []
        iowait = []
        idle = []      
        
        procstime = []
        cswchtime = []
        procs = []
        cswch = []     
        
        loadtime = []
        runq = []
        plist = []
        avg5min = []
        avg10min = []
        avg15min = []      
        
        memtime = []
        kbmemfree = []
        kbmemused = []
        kbcached = []
        kbswpfree = []     
        
        pswptime = []
        pswpin = []
        pswpout = []
        
        scktime = []
        misctime = []
        dentunusd = []
        file_nr = []
        inode_nr = []
        tcp_sck = []
        udp_sck = []
        
        blockstime = []
        bread = []
        bwrtn = []
        
        # for non-data masking
        
        masked_cputime = []
        masked_procstime = []
        masked_cswchtime = []
        masked_loadtime = []
        masked_memtime = []
        masked_pswptime = []
        masked_scktime = []
        masked_misctime = []
        masked_blockstime = []
        
        for graphdate, data_struct in sorted(self.data.items(), key = lambda x: x[0]):
                       
            cpu_captured = data_struct["cpu_captured"]
            procs_captured = data_struct["procs_captured"]
            cswch_captured = data_struct["cswch_captured"]
            load_captured = data_struct["load_captured"]
            mem_captured = data_struct["mem_captured"]
            swp_captured = data_struct["swp_captured"]
            pswp_captured = data_struct["pswp_captured"]
            misc_captured = data_struct["misc_captured"]
            sck_captured = data_struct["sck_captured"]
            blocks_captured = data_struct["blocks_captured"]
            
            restarts = data_struct["restarts"]
            
            get_time_func = lambda x: datetime.datetime.strptime(graphdate+" "+x[0], "%y-%m-%d %H:%M:%S")

            restarttime.extend(list(map(lambda x: get_time_func((x,)), restarts)))

            cputime.extend(list(map(get_time_func, cpu_captured)))
            masked_cputime.append(len(cputime))  
            
            if self.rhel_version == 5:                
                user.extend(list(map(lambda x: float(x[self.indeces.get('%user')]), cpu_captured)))         
            else:                
                user.extend(list(map(lambda x: float(x[self.indeces.get('%usr')]), cpu_captured)))
            
            nice.extend(list(map(lambda x: float(x[self.indeces.get("%nice")]), cpu_captured)))
            
            if self.rhel_version == 5:                
                system.extend(list(map(lambda x: float(x[self.indeces.get("%system")]), cpu_captured)))            
            else:               
                system.extend(list(map(lambda x: float(x[self.indeces.get("%sys")]), cpu_captured)))
            
            iowait.extend(list(map(lambda x: float(x[self.indeces.get("%iowait")]), cpu_captured)))
            idle.extend(list(map(lambda x: float(x[self.indeces.get("%idle")]), cpu_captured)))
            
            procstime.extend(list(map(get_time_func, procs_captured)))
            cswchtime.extend(list(map(get_time_func, cswch_captured)))
            masked_procstime.append(len(procstime))
            masked_cswchtime.append(len(cswchtime))
            procs.extend(list(map(lambda x: float(x[self.indeces.get('proc/s')]), procs_captured)))
            cswch.extend(list(map(lambda x: float(x[self.indeces.get('cswch/s')]), cswch_captured)))
            
            loadtime.extend(list(map(get_time_func, load_captured)))
            masked_loadtime.append(len(loadtime))
            runq.extend(list(map(lambda x: float(x[self.indeces.get('runq-sz')]), load_captured)))
            plist.extend(list(map(lambda x: float(x[self.indeces.get('plist-sz')]), load_captured)))
            avg5min.extend(list(map(lambda x: float(x[self.indeces.get('ldavg-1')]), load_captured)))
            avg10min.extend(list(map(lambda x: float(x[self.indeces.get('ldavg-5')]), load_captured)))
            avg15min.extend(list(map(lambda x: float(x[self.indeces.get('ldavg-15')]), load_captured)))
            
            memtime.extend(list(map(get_time_func, mem_captured)))
            masked_memtime.append(len(memtime))
            kbmemfree.extend(list(map(lambda x: float(x[self.indeces.get('kbmemfree')]) / 1024 / 1024, mem_captured)))
            kbmemused.extend(list(map(lambda x: float(x[self.indeces.get('kbmemused')]) / 1024 / 1024, mem_captured)))
            kbcached.extend(list(map(lambda x: float(x[self.indeces.get('kbcached')]) / 1024 / 1024, mem_captured)))
            
            if self.rhel_version == 5:                            
                kbswpfree.extend(list(map(lambda x: float(x[self.indeces.get('kbswpfree')]) / 1024 / 1024, mem_captured)))            
            else:                
                kbswpfree.extend(list(map(lambda x: float(x[self.indeces.get('kbswpfree')]) / 1024 / 1024, swp_captured)))    
            
            
            pswptime.extend(list(map(get_time_func, pswp_captured)))
            masked_pswptime.append(len(pswptime))
            pswpin.extend(list(map(lambda x: float(x[self.indeces.get('pswpin/s')]), pswp_captured)))
            pswpout.extend(list(map(lambda x: float(x[self.indeces.get('pswpout/s')]), pswp_captured)))
            
            misctime.extend(list(map(get_time_func, misc_captured)))
            masked_misctime.append(len(misctime))
            dentunusd.extend(list(map(lambda x: float(x[self.indeces.get('dentunusd')]), misc_captured)))
            
            if self.rhel_version == 5:            
                file_nr.extend(list(map(lambda x: float(x[self.indeces.get('file-sz')]), misc_captured)))
                inode_nr.extend(list(map(lambda x: float(x[self.indeces.get('inode-sz')]), misc_captured)))
            
            else:                
                file_nr.extend(list(map(lambda x: float(x[self.indeces.get('file-nr')]), misc_captured)))
                inode_nr.extend(list(map(lambda x: float(x[self.indeces.get('inode-nr')]), misc_captured)))
            
            scktime.extend(list(map(get_time_func, sck_captured)))
            masked_scktime.append(len(scktime))
            tcp_sck.extend(list(map(lambda x: float(x[self.indeces.get('tcpsck')]), sck_captured)))
            udp_sck.extend(list(map(lambda x: float(x[self.indeces.get('udpsck')]), sck_captured)))
            
            blockstime.extend(list(map(get_time_func, blocks_captured)))
            masked_blockstime.append(len(blockstime))  
            bread.extend(list(map(lambda x: float(x[self.indeces.get('bread/s')]), blocks_captured)))
            bwrtn.extend(list(map(lambda x: float(x[self.indeces.get('bwrtn/s')]), blocks_captured)))
            
            
            
        if plot_cpu: # CPU usage graph plot
                        
            plt.style.use('/usr/share/asap-graph/mystyle.mplstyle')
            
             
            plt.subplot2grid((2,2), (0, 0), colspan=2)
            
            user = ma.MaskedArray(user)
            nice = ma.MaskedArray(nice)
            system = ma.MaskedArray(system)
            iowait = ma.MaskedArray(iowait)
            idle = ma.MaskedArray(idle)
            if masked_cputime:
                for m in masked_cputime[:-1]:
                    user[m] = ma.masked
                    nice[m] = ma.masked
                    system[m] = ma.masked
                    iowait[m] = ma.masked
                    idle[m] = ma.masked
            
            plt.plot(np.array(cputime), user, label="%user")
            plt.plot(np.array(cputime), nice, label="%nice")
            plt.plot(np.array(cputime), system, label="%system")
            plt.plot(np.array(cputime), iowait, label="%iowait")
            plt.plot(np.array(cputime), idle, label="%idle")        
            plt.plot([], [], label=self.cpu_num, color='black', marker='+', markeredgewidth=3, markersize=3)
            
            if len(restarttime) > 0:
                [plt.axvline(_x, linestyle="dashed", color='r', label='RESTART' if not i else None, zorder=5) for i, _x in enumerate(restarttime)]
            
            lgd = plt.legend(ncol=1, loc='best')
            lgd.get_frame().set_alpha(0)
            
            ymin, ymax = plt.ylim()
            ydiff = (ymax - ymin)* 0.05
            ymin -= ydiff
            ymax += ydiff
            plt.ylim(ymin, ymax)
            
            plt.xticks(rotation=30)
                        
            plt.subplot2grid((2,2), (1, 0))
            
            procs = ma.MaskedArray(procs)
            if masked_procstime:
                for m in masked_procstime[:-1]:
                    procs[m] = ma.masked
            
            plt.plot(np.array(procstime), procs, label="procs/s", color='c')
            
            if len(restarttime) > 0:
                [plt.axvline(_x, linestyle="dashed", color='r', label='RESTART' if not i else None, zorder=5) for i, _x in enumerate(restarttime)]
            
            lgd = plt.legend(ncol=1, loc='best')
            lgd.get_frame().set_alpha(0)
            
            ymin, ymax = plt.ylim()
            ydiff = (ymax - ymin)* 0.05
            ymin -= ydiff
            ymax += ydiff
            plt.ylim(ymin, ymax)
            
            plt.xticks(rotation=30)          

            plt.subplot2grid((2,2), (1, 1))
            
            cswch = ma.MaskedArray(cswch)
            if masked_cswchtime:
                for m in masked_cswchtime[:-1]:
                    cswch[m] = ma.masked
            
            plt.plot(np.array(cputime), cswch, label="cswch/s", color='g')
            
            if len(restarttime) > 0:
                [plt.axvline(_x, linestyle="dashed", color='r', label='RESTART' if not i else None, zorder=5) for i, _x in enumerate(restarttime)]
            
            lgd = plt.legend(ncol=1, loc='best')
            lgd.get_frame().set_alpha(0)
            
            ymin, ymax = plt.ylim()
            ydiff = (ymax - ymin)* 0.05
            ymin -= ydiff
            ymax += ydiff
            plt.ylim(ymin, ymax)
            
            plt.xticks(rotation=30)
                      
            fig = plt.gcf()
            fig.set_size_inches(16.00, 09.00)
            
            plt.tight_layout()
            plt.savefig((save_name + "_CPU.png"), bbox_extra_artists=(lgd,), dpi = 100)
            plt.clf()
                     
        if plot_load: # load graph plot

            plt.style.use('/usr/share/asap-graph/mystyle.mplstyle')
            
            plt.subplot(311)
            
            avg5min = ma.MaskedArray(avg5min)
            avg10min = ma.MaskedArray(avg10min)
            avg15min = ma.MaskedArray(avg15min)
            if masked_loadtime:
                for m in masked_loadtime[:-1]:
                    avg5min[m] = ma.masked
                    avg10min[m] = ma.masked
                    avg15min[m] = ma.masked

            
            plt.plot(np.array(loadtime), avg5min, label="avg5min", color='#595b01')
            plt.plot(np.array(loadtime), avg10min, label="avg10min", color='#ffe600')
            plt.plot(np.array(loadtime), avg15min, label="avg15min", color='#fe7d00')
            plt.plot([], [], label=self.cpu_num, color='black', marker='+', markeredgewidth=3, markersize=3)
            
            if len(restarttime) > 0:
                [plt.axvline(_x, linestyle="dashed", color='r', label='RESTART' if not i else None, zorder=5) for i, _x in enumerate(restarttime)]
            
            lgd = plt.legend(ncol=1, loc='best')
            lgd.get_frame().set_alpha(0)
            
            ymin, ymax = plt.ylim()
            ydiff = (ymax - ymin)* 0.05
            ymin -= ydiff
            ymax += ydiff
            plt.ylim(ymin, ymax)
            
            plt.xticks(rotation=30)
            
            plt.subplot(312)
            
            runq = ma.MaskedArray(runq)
            if masked_loadtime:
                for m in masked_loadtime[:-1]:
                    runq[m] = ma.masked
            
            plt.plot(np.array(loadtime), runq, label="runq", color='#fec842')
            
            if len(restarttime) > 0:
                [plt.axvline(_x, linestyle="dashed", color='r', label='RESTART' if not i else None, zorder=5) for i, _x in enumerate(restarttime)]
            
            lgd = plt.legend(ncol=1, loc='best')
            lgd.get_frame().set_alpha(0)
            
            ymin, ymax = plt.ylim()
            ydiff = (ymax - ymin)* 0.05
            ymin -= ydiff
            ymax += ydiff
            plt.ylim(ymin, ymax)
            
            plt.xticks(rotation=30)

         
            plt.subplot(313)
            
            plist = ma.MaskedArray(plist)
            if masked_loadtime:
                for m in masked_loadtime[:-1]:
                    plist[m] = ma.masked

            
            plt.plot(np.array(loadtime), plist, label="plist", color='#e97a2e')
                        
            if len(restarttime) > 0:
                [plt.axvline(_x, linestyle="dashed", color='r', label='RESTART' if not i else None, zorder=5) for i, _x in enumerate(restarttime)]
            
            lgd = plt.legend(ncol=1, loc='best')
            lgd.get_frame().set_alpha(0)
            
            ymin, ymax = plt.ylim()
            ydiff = (ymax - ymin)* 0.05
            ymin -= ydiff
            ymax += ydiff
            plt.ylim(ymin, ymax)
            
            plt.xticks(rotation=30)
                      
            fig = plt.gcf()
            fig.set_size_inches(16.00, 09.00)
            
            plt.tight_layout()
            plt.savefig((save_name + "_load.png"), bbox_extra_artists=(lgd,), dpi = 100)
            plt.cla()
            plt.clf()          
        
        if plot_memory: # memory usage graph plot
        
            plt.style.use('/usr/share/asap-graph/mystyle.mplstyle')
           
            kbmemfree = ma.MaskedArray(kbmemfree)
            kbmemused = ma.MaskedArray(kbmemused)
            kbcached = ma.MaskedArray(kbcached)
            kbswpfree = ma.MaskedArray(kbswpfree)
            if masked_memtime:
                for m in masked_memtime[:-1]:
                    kbmemfree[m] = ma.masked
                    kbmemused[m] = ma.masked
                    kbcached[m] = ma.masked
                    kbswpfree[m] = ma.masked
       
            plt.plot(np.array(memtime), kbmemfree, label="memfree/GB")
            plt.plot(np.array(memtime), kbmemused, label="memused/GB")
            plt.plot(np.array(memtime), kbcached, label="cacheused/GB")       
            plt.plot(np.array(memtime), kbswpfree, label="kbswpfree/GB")
            
            if len(restarttime) > 0:
                [plt.axvline(_x, linestyle="dashed", color='r', label='RESTART' if not i else None, zorder=5) for i, _x in enumerate(restarttime)]
            
            lgd = plt.legend(ncol=1, loc='best')
            lgd.get_frame().set_alpha(0)
            
            ymin, ymax = plt.ylim()
            ydiff = (ymax - ymin)* 0.05
            ymin -= ydiff
            ymax += ydiff
            plt.ylim(ymin, ymax)
            
            plt.xticks(rotation=30)
                      
            fig = plt.gcf()
            fig.set_size_inches(16.00, 09.00)
            
            plt.tight_layout()
            plt.savefig((save_name + "_memory.png"), bbox_extra_artists=(lgd,), dpi = 100)
            plt.clf()
     
        if plot_misc: # m isc graph plot

            plt.style.use('/usr/share/asap-graph/mystyle.mplstyle')
            
            plt.subplot2grid((2,2), (0, 0))

            file_nr = ma.MaskedArray(file_nr)
            if masked_misctime:
                for m in masked_misctime[:-1]:
                    file_nr[m] = ma.masked

            plt.plot(np.array(misctime), file_nr, label="file_nr")
            
            if len(restarttime) > 0:
                [plt.axvline(_x, linestyle="dashed", color='r', label='RESTART' if not i else None, zorder=5) for i, _x in enumerate(restarttime)]
            
            lgd = plt.legend(ncol=1, loc='best')
            lgd.get_frame().set_alpha(0)
            
            ymin, ymax = plt.ylim()
            ydiff = (ymax - ymin)* 0.05
            ymin -= ydiff
            ymax += ydiff
            plt.ylim(ymin, ymax)
            
            plt.xticks(rotation=30)
            
            plt.subplot2grid((2,2), (0, 1))

            inode_nr = ma.MaskedArray(inode_nr)
            dentunusd = ma.MaskedArray(dentunusd)
            if masked_misctime:
                for m in masked_misctime[:-1]:
                    inode_nr[m] = ma.masked
                    dentunusd[m] = ma.masked
            
            plt.plot(np.array(misctime), inode_nr, label="inode_nr")
            plt.plot(np.array(misctime), dentunusd, label="dentunusd")
            
            if len(restarttime) > 0:
                [plt.axvline(_x, linestyle="dashed", color='r', label='RESTART' if not i else None, zorder=5) for i, _x in enumerate(restarttime)]
            
            lgd = plt.legend(ncol=1, loc='best')
            lgd.get_frame().set_alpha(0)
            
            ymin, ymax = plt.ylim()
            ydiff = (ymax - ymin)* 0.05
            ymin -= ydiff
            ymax += ydiff
            plt.ylim(ymin, ymax)
            
            plt.xticks(rotation=30)
           
            plt.subplot2grid((2,2), (1, 0), colspan=2)
                        
            tcp_sck = ma.MaskedArray(tcp_sck)
            udp_sck = ma.MaskedArray(udp_sck)
            if masked_scktime:
                for m in masked_scktime[:-1]:
                    tcp_sck[m] = ma.masked
                    udp_sck[m] = ma.masked
                        
            plt.plot(np.array(scktime), tcp_sck, label="tcp_sck", color='c')
            plt.plot(np.array(scktime), udp_sck, label="udp_sck", color='m')
            
   
            
            if len(restarttime) > 0:
                [plt.axvline(_x, linestyle="dashed", color='r', label='RESTART' if not i else None, zorder=5) for i, _x in enumerate(restarttime)]
            
            lgd = plt.legend(ncol=1, loc='best')
            lgd.get_frame().set_alpha(0)
            
            ymin, ymax = plt.ylim()
            ydiff = (ymax - ymin)* 0.05
            ymin -= ydiff
            ymax += ydiff
            plt.ylim(ymin, ymax)
            
            plt.xticks(rotation=30)
                                  
            fig = plt.gcf()
            fig.set_size_inches(16.00, 09.00)
            
            plt.tight_layout()
            plt.savefig((save_name + "_misc.png"), bbox_extra_artists=(lgd,), dpi = 100)
            plt.cla() 
       
        if plot_blocks:
       
            plt.style.use('/usr/share/asap-graph/mystyle.mplstyle')
            
            plt.subplot(211)
            
            bread = ma.MaskedArray(bread)
            if masked_blockstime:
                for m in masked_loadtime[:-1]:
                    bread[m] = ma.masked
            
            plt.plot(np.array(loadtime), bread, label="bread/s", color='#E95D22')
            
            if len(restarttime) > 0:
                [plt.axvline(_x, linestyle="dashed", color='r', label='RESTART' if not i else None, zorder=5) for i, _x in enumerate(restarttime)]
            
            lgd = plt.legend(ncol=1, loc='best')
            lgd.get_frame().set_alpha(0)
            
            ymin, ymax = plt.ylim()
            ydiff = (ymax - ymin)* 0.05
            ymin -= ydiff
            ymax += ydiff
            plt.ylim(ymin, ymax)
            
            plt.xticks(rotation=30)
            
            plt.subplot(212)
            
            bwrtn = ma.MaskedArray(bwrtn)
            if masked_loadtime:
                for m in masked_loadtime[:-1]:
                    bwrtn[m] = ma.masked
            
            plt.plot(np.array(loadtime), bwrtn, label="bwrtn/s", color='#017890')
            
            if len(restarttime) > 0:
                [plt.axvline(_x, linestyle="dashed", color='r', label='RESTART' if not i else None, zorder=5) for i, _x in enumerate(restarttime)]
            
            lgd = plt.legend(ncol=1, loc='best')
            lgd.get_frame().set_alpha(0)
            
            ymin, ymax = plt.ylim()
            ydiff = (ymax - ymin)* 0.05
            ymin -= ydiff
            ymax += ydiff
            plt.ylim(ymin, ymax)
            
            plt.xticks(rotation=30)
       
            fig = plt.gcf()
            fig.set_size_inches(16.00, 09.00)
            
            plt.tight_layout()
            plt.savefig((save_name + "_blocks.png"), bbox_extra_artists=(lgd,), dpi = 100)
            plt.cla() 
       
        if plot_overview: # all in one graph plot
        
            plt.style.use('/usr/share/asap-graph/mystyle.mplstyle')         
            
                # CPU
            
            plt.subplot2grid((3,4), (0,0), colspan=2)
            
            user = ma.MaskedArray(user)
            nice = ma.MaskedArray(nice)
            system = ma.MaskedArray(system)
            iowait = ma.MaskedArray(iowait)
            idle = ma.MaskedArray(idle)
            if masked_cputime:
                for m in masked_cputime[:-1]:
                    user[m] = ma.masked
                    nice[m] = ma.masked
                    system[m] = ma.masked
                    iowait[m] = ma.masked
                    idle[m] = ma.masked
                      
            plt.plot(np.array(cputime), user, label="%user", color='#e73571') 
            plt.plot(np.array(cputime), nice, label="%nice", color='#f0e3d5')
            plt.plot(np.array(cputime), system, label="%sys", color='#ff9302')
            plt.plot(np.array(cputime), iowait, label="%iowait", color='#0382aa')
            plt.plot(np.array(cputime), idle, label="%idle", color='#000e17')
            plt.plot([], [], label=self.cpu_num, color='black', marker='+', markeredgewidth=3, markersize=3)
            
            
            if len(restarttime) > 0:
                [plt.axvline(_x, linestyle="dashed", color='r', label='RESTART' if not i else None, zorder=5) for i, _x in enumerate(restarttime)]
            
            lgd = plt.legend(ncol=3, loc='best')
            lgd.get_frame().set_alpha(0)
            
            ymin, ymax = plt.ylim()
            ydiff = (ymax - ymin)* 0.05
            ymin -= ydiff
            ymax += ydiff
            plt.ylim(ymin, ymax)
            
            plt.xticks(rotation=30)
            
            
                # LOAD
            
            plt.subplot2grid((3,4), (0, 2), colspan=2)
            
            avg5min = ma.MaskedArray(avg5min)
            avg10min = ma.MaskedArray(avg10min)
            avg15min = ma.MaskedArray(avg15min)
            if masked_loadtime:
                for m in masked_loadtime[:-1]:
                    avg5min[m] = ma.masked
                    avg10min[m] = ma.masked
                    avg15min[m] = ma.masked
                    
            plt.plot(np.array(loadtime), avg5min, label="avg5min", color='#595b01')
            plt.plot(np.array(loadtime), avg10min, label="avg10min", color='#ffe600')
            plt.plot(np.array(loadtime), avg15min, label="avg15min", color='#fe7d00')
            plt.plot([], [], label=self.cpu_num, color='black', marker='+', markeredgewidth=3, markersize=3)
            
            if len(restarttime) > 0:
                [plt.axvline(_x, linestyle="dashed", color='r', label='RESTART' if not i else None, zorder=5) for i, _x in enumerate(restarttime)]
            
            lgd = plt.legend(ncol=2, loc='best')
            lgd.get_frame().set_alpha(0)
            
            ymin, ymax = plt.ylim()
            ydiff = (ymax - ymin)* 0.05
            ymin -= ydiff
            ymax += ydiff
            plt.ylim(ymin, ymax)
            
            plt.xticks(rotation=30)
            
                # MEMORY
                
            plt.subplot2grid((3,4), (1, 0), colspan=2)  
            
            kbmemfree = ma.MaskedArray(kbmemfree)
            kbmemused = ma.MaskedArray(kbmemused)
            kbcached = ma.MaskedArray(kbcached)
            kbswpfree = ma.MaskedArray(kbswpfree)
            if masked_memtime:
                for m in masked_memtime[:-1]:
                    kbmemfree[m] = ma.masked
                    kbmemused[m] = ma.masked
                    kbcached[m] = ma.masked
                    kbswpfree[m] = ma.masked
            
            plt.plot(np.array(memtime), kbmemfree, label="memfree/GB", color='#a42102')
            plt.plot(np.array(memtime), kbmemused, label="memused/GB", color='#da7701')
            plt.plot(np.array(memtime), kbcached, label="cacheused/GB", color='#fdc700')       
            plt.plot(np.array(memtime), kbswpfree, label="swpfree/GB", color='#77dd77')
            
            if len(restarttime) > 0:             
                [plt.axvline(_x, linestyle="dashed", color='r', label='RESTART' if not i else None, zorder=5) for i, _x in enumerate(restarttime)]
            
            lgd = plt.legend(ncol=3, loc='best')
            lgd.get_frame().set_alpha(0)          

            ymin, ymax = plt.ylim()
            ydiff = (ymax - ymin)* 0.05
            ymin -= ydiff
            ymax += ydiff
            plt.ylim(ymin, ymax)

            plt.xticks(rotation=30)
                
                # PSWP

            plt.subplot2grid((3,4), (1, 2))
            
            pswpin = ma.MaskedArray(pswpin)
            pswpout = ma.MaskedArray(pswpout)
            if masked_pswptime:
                for m in masked_pswptime[:-1]:
                    pswpin[m] = ma.masked
                    pswpout[m] = ma.masked

            
            plt.plot(np.array(pswptime), pswpin, label="pswpin", color='#fe7e0f')
            plt.plot(np.array(pswptime), pswpout, label="pswpout", color='#8e3ccb')
            
            if len(restarttime) > 0:
                [plt.axvline(_x, linestyle="dashed", color='r', label='RESTART' if not  i else None, zorder=5) for i, _x in enumerate(restarttime)]
            
            lgd = plt.legend(ncol=1, loc='best')
            lgd.get_frame().set_alpha(0)
            ymin, ymax = plt.ylim()

            ymin, ymax = plt.ylim()
            ydiff = (ymax - ymin)* 0.05
            ymin -= ydiff
            ymax += ydiff
            plt.ylim(ymin, ymax)

            plt.xticks(rotation=30)
            
                # PROC/S
            
            plt.subplot2grid((3,4), (1, 3))
            
            procs = ma.MaskedArray(procs)
            if masked_procstime:
                for m in masked_procstime[:-1]:
                    procs[m] = ma.masked
            
            plt.plot(np.array(procstime), procs, label="proc/s", color='#e64313')
            
            if len(restarttime) > 0:
                [plt.axvline(_x, linestyle="dashed", color='r', label='RESTART' if not i else None, zorder=5) for i, _x in enumerate(restarttime)]
            
            lgd = plt.legend(ncol=1, loc='best')
            lgd.get_frame().set_alpha(0)
            
            ymin, ymax = plt.ylim()
            ydiff = (ymax - ymin)* 0.05
            ymin -= ydiff
            ymax += ydiff
            plt.ylim(ymin, ymax)
            
            plt.xticks(rotation=30)
            
                # CSWCH
            
            plt.subplot2grid((3,4), (2, 0))
            
            cswch = ma.MaskedArray(cswch)
            if masked_cswchtime:
                for m in masked_cswchtime[:-1]:
                    cswch[m] = ma.masked
            
            plt.plot(np.array(cswchtime), cswch, label="cswch/s", color='#9c9d47')
            
            if len(restarttime) > 0:
                [plt.axvline(_x, linestyle="dashed", color='r', label='RESTART' if not i else None, zorder=5) for i, _x in enumerate(restarttime)]
            
            lgd = plt.legend(ncol=1, loc='best')
            lgd.get_frame().set_alpha(0)
            
            ymin, ymax = plt.ylim()
            ydiff = (ymax - ymin)* 0.05
            ymin -= ydiff
            ymax += ydiff
            plt.ylim(ymin, ymax)
            
            plt.xticks(rotation=30)
                                    
               # RUNQ        
                         
            plt.subplot2grid((3,4), (2, 1))
            
            runq = ma.MaskedArray(runq)
            if masked_cswchtime:
                for m in masked_loadtime[:-1]:
                    runq[m] = ma.masked
            
            plt.plot(np.array(loadtime), runq, label="runq", color='#fec842')
            
            if len(restarttime) > 0:
                [plt.axvline(_x, linestyle="dashed", color='r', label='RESTART' if not i else None, zorder=5) for i, _x in enumerate(restarttime)]
            
            lgd = plt.legend(ncol=1, loc='best')
            lgd.get_frame().set_alpha(0)
            
            ymin, ymax = plt.ylim()
            ydiff = (ymax - ymin)* 0.05
            ymin -= ydiff
            ymax += ydiff
            plt.ylim(ymin, ymax)
            
            plt.xticks(rotation=30)
                 
                 # PLIST
            
            plt.subplot2grid((3,4), (2, 2))
            
            plist = ma.MaskedArray(plist)
            if masked_cswchtime:
                for m in masked_loadtime[:-1]:
                    plist[m] = ma.masked
            
            plt.plot(np.array(loadtime), plist, label="plist", color='#e97a2e')
                        
            if len(restarttime) > 0:
                [plt.axvline(_x, linestyle="dashed", color='r', label='RESTART' if not i else None, zorder=5) for i, _x in enumerate(restarttime)]
            
            lgd = plt.legend(ncol=1, loc='best')
            lgd.get_frame().set_alpha(0)
            
            ymin, ymax = plt.ylim()
            ydiff = (ymax - ymin)* 0.05
            ymin -= ydiff
            ymax += ydiff
            plt.ylim(ymin, ymax)
            
            plt.xticks(rotation=30)
            
                # SOCKETS
            
            plt.subplot2grid((3,4), (2, 3))
            
            tcp_sck = ma.MaskedArray(tcp_sck)
            udp_sck = ma.MaskedArray(udp_sck)
            if masked_scktime:
                for m in masked_scktime[:-1]:
                    tcp_sck[m] = ma.masked
                    udp_sck[m] = ma.masked
            
            plt.plot(np.array(scktime), tcp_sck, label="tcpsck", color='#834e71')
            plt.plot(np.array(scktime), udp_sck, label="udpsck", color='#88d5d2')
            
            if len(restarttime) > 0:
                [plt.axvline(_x, linestyle="dashed", color='r', label='RESTART' if not i else None, zorder=5) for i, _x in enumerate(restarttime)]
            
            lgd = plt.legend(ncol=1, loc='best')
            lgd.get_frame().set_alpha(0)
            
            ymin, ymax = plt.ylim()
            ydiff = (ymax - ymin)* 0.05
            ymin -= ydiff
            ymax += ydiff
            plt.ylim(ymin, ymax)
            
            plt.xticks(rotation=30)
                      
            fig = plt.gcf()
            fig.set_size_inches(19.20, 10.80)
            plt.tight_layout()
            plt.savefig((save_name + "_overview.png"), bbox_extra_artists=(lgd,), dpi = 100)
            plt.cla()
                        
if __name__ == "__main__":
        
    try:

        arguments = docopt(__doc__)

        if (arguments['file']) == True:
            
            if arguments['-p'] != None and not os.path.exists(arguments['-p']):
                          
                print(Bcolors.FAIL + ('The path "%s" is not valid or does not exist!' % "".join(arguments['-p'])) + Bcolors.ENDC)
                exit(1)
                                        
            for sarfile in arguments['FILE']:
                
                s = SARAnalyzer()
                s.get_data(sarfile)
                s.generate_graphs(plot_all = arguments['-a'], plot_overview = arguments['-o'], plot_cpu = arguments['-c'], 
                                  plot_load = arguments['-l'], plot_memory = arguments['-m'], plot_misc = arguments['-s'], 
                                  plot_blocks = arguments['-b'], save_path = arguments['-p'])
              
        if (arguments['xp']) == True:
              
            if arguments['-p'] != None and not os.path.exists(arguments['-p']):
                          
                print(Bcolors.FAIL + ('The path "%s" is not valid or does not exist!' % "".join(arguments['-p'])) + Bcolors.ENDC)
                exit(1)
            
            if arguments['-x'] != None and not os.path.exists(arguments['-x']):
                          
                print(Bcolors.FAIL + ('The path "%s" is not valid or does not exist!' % "".join(arguments['-x'])) + Bcolors.ENDC)
                exit(1)
              
            s = SARAnalyzer()
            
            if arguments['-x'] != None:
                sarfiles = s.get_sars_recursively(arguments['-x'])                 
            
            else:
                sarfiles = s.get_sars_recursively()
            
            for sarfile in sarfiles:
                s = SARAnalyzer() 
                s.get_data(sarfile)             
                s.generate_graphs(plot_all = arguments['-a'], plot_overview = arguments['-o'], plot_cpu = arguments['-c'], 
                              plot_load = arguments['-l'], plot_memory = arguments['-m'], plot_misc = arguments['-s'], 
                              plot_blocks = arguments['-b'], save_path = arguments['-p'])
                              
                             
        if (arguments['cat']) == True:
            
            if arguments['-p'] != None and not os.path.exists(arguments['-p']):
                          
                print(Bcolors.FAIL + ('The path "%s" is not valid or does not exist!' % str(arguments['-p'])) + Bcolors.ENDC)
                exit(1)
            
            s = SARAnalyzer()
            sarfiles = complete_concat_sars(arguments['FILE'])

            for sarfile in sarfiles:

                s.get_data(sarfile)

            s.generate_graphs(plot_all = arguments['-a'], plot_overview = arguments['-o'], plot_cpu = arguments['-c'], 
                              plot_load = arguments['-l'], plot_memory = arguments['-m'], plot_misc = arguments['-s'], 
                              plot_blocks = arguments['-b'], save_path = arguments['-p'])
    except IsADirectoryError:
        print(Bcolors.FAIL + "Path provided, expected file!" + Bcolors.ENDC)
        exit(1)                                                                                                    
    except KeyboardInterrupt:
        print()
        print(Bcolors.FAIL + "The process was terminated!" + Bcolors.ENDC)
