#!/usr/bin/env python
"""Optimize free fluxes and optionaly metabolite concentrations of a given static metabolic network defined in an FTBL file to fit 13C data provided in the same FTBL file."
"""
import sys, os, datetime as dt, subprocess as subp
from optparse import OptionParser
from threading import Thread, enumerate as th_enum
from time import sleep

def now_s():
    return(dt.datetime.strftime(dt.datetime.now(), "%Y-%m-%d %H:%M:%S"))

def optional_pval(pval):
    def func(option,opt_str,value,parser):
        if parser.rargs and not parser.rargs[0].startswith('-'):
            try:
                val=float(parser.rargs[0])
                parser.rargs.pop(0)
            except:
                val=pval
        else:
            val=pval
        setattr(parser.values,option.dest,val)
    return func

def launch_compil(ft, fshort, cmd_opts):
    r"""Launch R code generation and then its execution
"""
    #print "here thread: "+fshort
    f=ft[:-5]
    flog=open(f+".log", "wb")
    ferr=open(f+".err", "wb")
    flog.write(" ".join('"'+v+'"' for v in sys.argv)+"\n")

    # code generation
    s=fshort+"code gen: "+now_s()
    flog.write(s+"\n")
    flog.flush()
    print(s)

    try:
        # generate the R code
        # leave python options as are and put R options as argument to --ropts
        opt4py=list(pyopt.intersection("--"+kc for kc in cmd_opts.keys())) + \
            ["--ropts", '"' + "; ".join(k+"="+("'"+v+"'" \
            if isinstance(v, type("")) else "T" if v is True else "F" \
            if v is False else str(v)) for k,v in cmd_opts.iteritems()) + '"'] \
            + [ft]
        pycmd=["python", os.path.join(direx, "ftbl2optR.py")] + opt4py
        #print(pycmd)
        p=subp.check_call(pycmd, stdout=flog, stderr=ferr)
        flog.close()
        ferr.close()

        # execute R code
        #rcmd="R --vanilla --slave".split()
        #flog.write("executing: "+" ".join(rcmd)+" <"+f+".R >>"+flog.name+" 2>>"+ferr.name+"\n")
        #s=fshort+"calcul  : "+now_s()
        #flog.write(s+"\n")
        #flog.flush()
        #print(s)
        #try:
        #    p=subp.check_call(rcmd, stdin=open(f+".R", "rb"), stdout=flog, stderr=ferr)
        #except:
        #    pass
        #ferr.close()
        #s=fshort+"end     : "+now_s()
        #print(s)
        #flog.write(s+"\n")
        #if os.path.getsize(ferr.name) > 0:
        #    s="=>Check "+ferr.name
        #    print(s)
        #    flog.write(s+"\n")
        #flog.close()
    except:
        flog.close()
        ferr.close()
        pass

pla=sys.platform
# my own name
me=os.path.realpath(sys.argv[0])
# my exec dir
direx=os.path.dirname(me)
direx="." if not direx else direx

sys.path.append(direx)
from kvh import escape

# my version
version=file(os.path.join(direx, "influx_version.txt"), "rb").read().strip()

# valid options for python
pyopt=set(("--fullsys", "--emu", "--DEBUG"))

# create a parser for command line options
parser = OptionParser(usage="usage: %prog [options] /path/to/FTBL_file1 [FTBL_file2 [...]]",
    description=__doc__,
    version="%prog "+version)
parser.add_option(
"--noopt", action="store_true",
    help="no optimization, just use free parameters as is (after a projection on feasability domain), to calculate dependent fluxes, cumomers, stats and so on")
parser.add_option(
"--noscale", action="store_true",
    help="no scaling factors to optimize => all scaling factors are assumed to be 1")
parser.add_option(
"--meth", type="choice",
    choices=["BFGS", "Nelder-Mead", "ipopt", "nlsic"],
    help="method for optimization, one of nlsic|BFGS|Nelder-Mead. Default: nlsic")
parser.add_option(
"--fullsys", action="store_true",
    help="calculate all cumomer set (not just the reduced one necesary to simulate measurements)")
parser.add_option(
"--emu", action="store_true",
    help="simulate labeling in EMU approach")
parser.add_option(
"--irand", action="store_true",
    help="ignore initial approximation for free parameters (free fluxes and metabolite concentrations) from the FTBL file or from a dedicated file (cf --fseries and --iseries option) and use random values drawn uniformly from [0,1] interval")
parser.add_option(
"--sens",
    help="sensitivity method: SENS can be 'mc[=N]', mc stands for Monte-Carlo. N is an optional number of Monte-Carlo simulations. Default for N: 10")
parser.add_option(
"--cupx", type="float",
    help="upper limit for reverse fluxes. Must be in interval [0, 1]. Default: 0.999")
parser.add_option(
"--cupn", type="float",
    help="upper limit for net fluxes. Default: 1.e3")
parser.add_option(
"--cupp", type="float",
    help="upper limit for metabolite pool. Default: 1.e5"),
parser.add_option(
"--clownr", type="float",
    help="lower limit for not reversible free and dependent fluxes. Zero value (default) means no lower limit")
parser.add_option(
"--cinout", type="float",
    help="lower limit for input/output free and dependent fluxes. Must be non negative. Default: 0")
parser.add_option(
"--clowp",
    help="lower limit for free metabolite pools. Must be positive. Default 1.e-8")
parser.add_option(
"--np", type="int", default=0,
    help="""Number of parallel process used in Monte-Carlo simulations on in case of multiple FTBL files submitted simultaneously. Without this option or for NP=0 all available cores in a given node are used""")
parser.add_option(
"--ln", action="store_true",
    help="Approximate least norm solution is used for increments during the non-linear iterations when Jacobian is rank deficient")
parser.add_option(
"--zc", type="float",
    help="Apply zero crossing strategy with non negative threshold for net fluxes")
parser.add_option(
"--fseries",
       help="File name with free parameter values for multiple starting points. Default: '' (empty, i.e. only one starting point from the FTBL file is used)"),
parser.add_option(
"--iseries",
       help="Indexes of starting points to use. Format: '1:10' -- use only first ten starting points; '1,3' -- use the the first and third starting points; '1:10,15,91:100' -- a mix of both formats is allowed. Default: '' (empty, i.e. all provided starting points are used)")
parser.add_option(
"--seed",
       help="Integer (preferably a prime integer) used for reproducible random number generating. It makes reproducible random starting points (--irand) but also Monte-Carlo simulations for sensitivity analysis (--sens mc=N) if executed in sequential way (--np=1). Default: current system value, i.e. random drawing will be varying at each run.")
parser.add_option(
"--excl_outliers", action='callback', callback=optional_pval(0.01), dest="excl_outliers",
       help="This option takes an optional argument, a p-value between 0 and 1 which is used to filter out measurement outliers. The filtering is based on Z statistics calculated on reduced residual distribution. Default: 0.01.")
parser.add_option(
"--DEBUG", action="store_true",
    help="developer option")
parser.add_option(
"--TIMEIT", action="store_true",
    help="developer option")
parser.add_option(
"--prof", action="store_true",
    help="developer option")

# parse commande line
(opts, args) = parser.parse_args()
#print ("opts=", opts)
#print ("args=", args)
# make args unique
args=set(args)
if len(args) < 1:
    parser.print_help()
    parser.error("At least one FTBL_file expected in argument")

print(" ".join('"'+v+'"' for v in sys.argv))

# add .ftbl where needed
args=[ft+(".ftbl" if ft[-5:] != ".ftbl" else "") for ft in args]
todel=[]
ths=[]
for ift in range(len(args)):
    ft=args[ift]
    if not os.path.exists(ft):
        sys.stderr.write("FTBL file '%s' does not exist."%ft)
        todel.append(ift)
        continue;
    f=ft[:-5]
    fshort="" if len(args) == 1 else os.path.basename(f)+": "

    # now parse commandArgs from the FTBL file
    cmd=""
    for line in open(ft, "rb"):
        if line[:13] == "\tcommandArgs\t":
            cmd=line[13:]
            break
    (cmd_opts, cmd_args) = parser.parse_args(cmd.split())
    #print ("cmd_opts=", cmd_opts)
    if len(cmd_args) != 0:
        ferr.write("Argument(s) '%s' from the field commandArgs of '%s' are ignored.\n"%(" ".join(cmd_args), ft))

    # update cmd_opts with runtime options
    cmd_opts._update_loose(dict((k,v) for (k,v) in eval(str(opts)).iteritems() if not v is None))
    cmd_opts=eval(str(cmd_opts))
    cmd_opts=dict((k,v) for k,v in cmd_opts.iteritems() if v is not None)
    #print("cmd_opts=", cmd_opts)
    th=Thread(target=launch_compil, name=ft, args=(ft, fshort, cmd_opts))
    th.start()
    ths.append(th)
for i in todel:
    del(args[i])

# wait untill all threads of compilation end
while True:
    if any(th.isAlive() for th in ths):
        # wait 0.1 s and loop again
        sleep(0.1)
    else:
        break

# R source are generated, generate and run par.R
fpar=open("par.R", "wb")
fpar.write("""
library(parallel)
suppressPackageStartupMessages(library(Matrix))
fvect=c(%(fvect)s)
run=function(f) {
   bn=basename(f)
   fshort=if (length(fvect) == 1) "" else sub(".R$", ": ", bn)
   scalc=paste(fshort, "calcul  : ", format(Sys.time(), "%(date)s"), "\\n", collapse="", sep="")
   source(f)
   cat(scalc, fshort, "end     : ", format(Sys.time(), "%(date)s"), "\\n", sep="")
   ferr=sub(".R$", ".err", f)
   if (file.info(ferr)$size > 0) {
      cat("=>Check ", ferr, "\\n", sep="")
   }
}
if (substr(R.Version()$os, 1, 5) == "mingw") {
   cl=makeCluster(%(np)s)
   clusterExport(cl, "fvect")
   res=parLapply(cl, fvect, run)
} else {
   res=mclapply(fvect, run)
}
"""%{
    "fvect": ", ".join(['"'+escape(ft, "\\")[:-5]+".R"+'"' for ft in args]),
    "date": "%Y-%m-%d %H:%M:%S",
    "np": str(cmd_opts["np"]) if cmd_opts.get("np") else "detectCores()"
})
fpar.close()
p=subp.check_call(["R", "--vanilla", "--slave"], stdin=open("par.R", "rb"))
sys.exit(0)
