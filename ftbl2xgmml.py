#!/usr/bin/python

r"""
read a .ftbl file from a parameter and translate to .xgmml file.
The generated xgmml file can be then imported into Cytoscape
(www.cytoscape.org).
Reactions involving two substrates or two products are represented
by an additional almost invisible node while one-to-one reactions
are just edges.
Node and edge attributes are written in respective xml attributes.
Compatibility: cytoscape v2.8.3 and v3.0

usage: ftbl2xgmml.py [-h|--help|--DEBUG] mynetwork.ftbl [> mynetwork.xgmml]

OPTIONS
-h, --help print this message and exit
--DEBUG enable some debuggin features and output (for developers only)

:param: mynetwork the base of an ftbl file (mynetwork.ftbl)

:returns: mynetwork.xgmml -- file of the network definition suitable for cytoscape

Copyright 2014, INRA, France
Author: Serguei Sokol (sokol at insa-toulouse dot fr)
License: Gnu Public License (GPL) v3 http://www.gnu.org/licenses/gpl.html
"""

# 2008-01-24 sokol. First trial (not working)
# 2014-01-29 sokol. Revamped into working state (based on ftbl2rsif.py)

if __name__ == "__main__":
    import sys
    import os
    import stat
    import getopt
    import re
    import math
    import random

    from tools_ssg import *
    from C13_ftbl import *

    werr=sys.stderr.write

    # determine colour of metabolite (in, out or plain)
    def color(m, netan, nc):
        return nc['i'] if m in netan['input'] \
            else nc['o'] if m in netan['output'] else \
            nc['m']

    #print sys.argv
    #exit()

    # Configurable constants
    ns={
        'm': 'roundrect',     # metabolite shape
        'r': 'ellipse'        # reaction shape
    }
    nc={
        'm': '255,255,255',    # metabolite colour
        'i': '0,255,0',        # input colour (uptake)
        'o': '255,0,0',        # output colour (escape)
        'r': '127,127,127'       # reaction colour
    }
    et={
        'nr': 'ARROW',       # not reversible target
        'r': 'ARROW',        # reversible target
    }
    es={
        'nr': 'NONE',        # not reversible source
        'r': 'CIRCLE',      # reversible source
    }
    # edge colours
    ec={
        'd': '0,0,255',    # dependent flux
        'c': '0,0,0',    # constrained flux
        'f': '0,255,0',    # free flux
    }
    # edge line style
    els={
        'nr': 'SOLID',
        'r': 'PARALLEL_LINES'
    }
    
    # node height and width in pixels
    n_h=30
    n_w=30
    # edge length in pixels
    e_l=70
    
    ##print 'start'
    # take arguments
    #<--skip in interactive session
    # get arguments
    me=os.path.basename(sys.argv[0])
    def usage():
        sys.stderr.write(__doc__)
    try:
        opts,args=getopt.getopt(sys.argv[1:], "h", ["help", "DEBUG"])
    except getopt.GetoptError, err:
        sys.stderr.write(str(err)+"\n")
        usage()
        sys.exit(1)
    cost=False
    DEBUG=False
    for o,a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o=="--DEBUG":
            DEBUG=True
    #aff("args", args);##
    if len(args) != 1:
        sys.stderr("Expecting exactly one ftbl file name\n")
        usage()
        exit(1)
    base=args[0]
    if base[-5:]==".ftbl":
        base=base[:-5]
    path_ftbl=base+".ftbl"
    #-->
    
    # what kind of output we have?
    mode=os.fstat(1).st_mode
    fout=sys.stdout if stat.S_ISFIFO(mode) or stat.S_ISREG(mode) else  open(path_ftbl[:-4]+"xgmml", "w")

    # define where to read and write
    # input file is an argument
    fdir=os.path.dirname(base) or "."
    base=os.path.basename(base)
    short_ftbl=base+".ftbl"
    ##    print base
    ##    print 'open files'

    # Parse .ftbl file
    try:
        ftbl=ftbl_parse(path_ftbl)
    except Exception as inst:
        werr(str(inst)+"\n")
        raise
    # Analyse the network
    try:
        netan=ftbl_netan(ftbl)
    except:
        #werr(str(sys.exc_info()[1])+"\n")
        raise
        #sys.exit(1)
    # transform metabs,reac in nodes (dict of promerties) and reac in edges (dict too)
    mlen=len(netan["metabs"])
    # graph dimensions
    gr_h=gr_w=math.sqrt(mlen)*(n_h+n_w+e_l)/3.
    
    # metabs -> nodes
    nodes={"metabs": {}, "reacs": {}}
    nodes["metabs"].update((metab,
        {"label": metab, "id": i+1, "shape": ns["m"],
        "color": nc["i"] if metab in netan["input"] else nc["o"] if metab in netan["output"] else nc["m"]})
        for (i, metab) in enumerate(netan["metabs"]))
    # reacs -> nodes
    nodes["reacs"].update((reac,
        {"label": reac, "id": i+1+mlen, "shape": ns["r"],
        "color": nc["r"]})
        for (i, (reac, d)) in enumerate((reac, d) for (reac, d) in netan["sto_r_m"].iteritems() if len(d["left"]) > 1 or len(d["right"]) > 1))
    # easy id finders
    metab2id=dict((m, d["id"]) for (m, d) in nodes["metabs"].iteritems())
    reac2id=dict((r, d["id"]) for (r, d) in nodes["reacs"].iteritems())
    
    # node numbers: total, width, height (for grid layout)
    nb_node=len(nodes["metabs"])+len(nodes["reacs"])
    nb_h=math.ceil(math.sqrt(nb_node))
    nb_w=math.ceil(math.sqrt(nb_node))
    nb_hh=nb_h/2
    nb_hw=nb_w/2
    for (m, d) in nodes["metabs"].iteritems():
        d["x"]=((d["id"]-1)%nb_w - nb_hw)*(n_w+e_l)
        d["y"]=(math.floor((d["id"]-1)/nb_h) - nb_hh)*(n_h+e_l)
    for (m, d) in nodes["reacs"].iteritems():
        d["x"]=((d["id"]-1)%nb_w - nb_hw)*(n_w+e_l)
        d["y"]=(math.floor((d["id"]-1)/nb_h) - nb_hh)*(n_h+e_l)
    
    # write header
    fout.write(
"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<graph id="1" label="%s" directed="1" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:cy="http://www.cytoscape.org" xmlns="http://www.cs.rpi.edu/XGMML">
  <att name="layoutAlgorithm" value="Grid Layout" type="string" cy:hidden="1"/>
  <graphics>
    <att name="network_center_x_location" value="0.0" type="string"/>
    <att name="network_scale_factor" value="1" type="string"/>
    <att name="network_edge_selection" value="true" type="string"/>
    <att name="network_center_y_location" value="0.0" type="string"/>
    <att name="network_node_selection" value="true" type="string"/>
    <att name="xnetwork_height" value="%f" type="string"/>
    <att name="network_background_paint" value="#ffffff" type="string"/>
    <att name="network_depth" value="0.0" type="string"/>
    <att name="xnetwork_width" value="%f" type="string"/>
    <att name="network_center_z_location" value="0.0" type="string"/>
  </graphics>
"""%(short_ftbl, gr_h, gr_w))
    # write metab nodes
    for (m, d) in nodes["metabs"].iteritems():
        fout.write("""
<node id="%(id)d" label="%(label)s" weight="1">
 <att type="string" name="node.shape" value="%(shape)s"/>
 <att type="string" name="node.label" value="%(label)s"/>
 <att name="node.toolTip" value="%(label)s" type="string"/>
 <graphics type="%(shape)s" h="30" w="30" width="3" fill="%(color)s" z="0" y="%(y).2f" x="%(x).2f">
  <att name="node_label_color" value="#000000" type="string"/>
  <att name="node_tooltip" value="%(label)s" type="string"/>
 </graphics>
</node>"""%d)
    # write reac nodes
    fout.write("\n")
    for (r, d) in nodes["reacs"].iteritems():
        fout.write("""
<node id="%(id)d" label="%(label)s" weight="0">
 <att type="string" name="node.shape" value="%(shape)s"/>
 <att type="string" name="node.label" value="%(label)s"/>
 <att type="string" name="node.width" value="3"/>
 <att type="string" name="node.height" value="3"/>
 <att type="string" name="node.toolTip" value="%(label)s"/>
 <graphics type="%(shape)s" w="3" h="3" fill="%(color)s" width="0" z="0" y="%(y).2f" x="%(x).2f">
  <att name="node_label_color" value="#000000" type="string"/>
  <att name="node_tooltip" value="%(label)s" type="string"/>
 </graphics>
</node>"""%d)
    # write edges
    fout.write("\n\n")
    for (r, d) in netan["sto_r_m"].iteritems():
        # reversible or not?
        rnr="nr" if r in netan["notrev"] else "r"
        # forward flux is dependent, free or constrained?
        fw_dfc=netan["nx2dfcg"]["n."+r][0]
        # revers flux is dependent, free or constrained?
        rv_dfc=netan["nx2dfcg"]["x."+r][0]
        eds=[] # list of dicts: name, ids of source and target, reac, source and target arrow shape, fw&rv color
        if r in reac2id:
            # complex reaction
            rid=reac2id[r]
            subs=d["left"] # substrates of this reaction
            prods=d["right"] # products of this reaction
            same_subs=len(subs)==2 and subs[0]==subs[1]
            same_prods=len(prods)==2 and prods[0]==prods[1]
            eds.extend({
               "label": m+" ("+r+(str(isu+1) if same_subs else "")+") "+r,
               "id_s": metab2id[m],
               "id_t": rid,
               "reac": r,
               "arr_s": es[rnr],
               "arr_t": "NONE",
               "col_s": ec[rv_dfc],
               "col_t": ec[fw_dfc],
               "line": els[rnr],
               } for (isu, m) in enumerate(subs))
            eds.extend({
               "label": r+" ("+r+(str(ipr+1) if same_prods else "")+") "+m,
               "id_s": rid,
               "id_t": metab2id[m],
               "reac": r,
               "arr_s": "NONE",
               "arr_t": et[rnr],
               "col_s": ec[rv_dfc],
               "col_t": ec[fw_dfc],
               "line": els[rnr],
               } for (ipr, m) in enumerate(prods))
        else:
            # simple reaction
            s=d["left"][0]
            t=d["right"][0]
            eds.append({
               "label": s+" ("+r+") "+t,
               "id_s": metab2id[s],
               "id_t": metab2id[t],
               "reac": r,
               "arr_s": es[rnr],
               "arr_t": et[rnr],
               "col_s": ec[rv_dfc],
               "col_t": ec[fw_dfc],
               "line": els[rnr],
               })
        for st in eds:
            fout.write(
"""<edge label="%(label)s" source="%(id_s)d" target="%(id_t)d" weight="1">
 <att name="reaction" value="%(reac)s" type="string"/>
 <att name="edge.toolTip" value="%(reac)s" type="string"/>
 <att name="edge.sourceArrowShape" value="%(arr_s)s" type="string"/>
 <att name="edge.targetArrowShape" value="%(arr_t)s" type="string"/>
 <att name="edge.sourceArrowColor" value="%(col_s)s" type="string"/>
 <att name="edge.targetArrowColor" value="%(col_t)s" type="string"/>
 <att name="edge.curved" value="true" type="string"/>
 <att name="edge.lineStyle" value="%(line)s" type="string"/>
 <graphics fill="#aaaaff">
  <att name="edge_tooltip" value="%(reac)s" type="string"/>
  <att name="edge_source_arrow_shape" value="%(arr_s)s" type="string"/>
  <att name="edge_target_arrow_shape" value="%(arr_t)s" type="string"/>
  <att name="edge_source_arrow_unselected_paint" value="%(col_s)s" type="string"/>
  <att name="edge_target_arrow_unselected_paint" value="%(col_t)s" type="string"/>
  <att name="edge_curved" value="true" type="string"/>
  <att name="edge_line_type" value="%(line)s" type="string"/>
 </graphics>
</edge>
"""%st)
    # print footer
    fout.write("</graph>\n")
