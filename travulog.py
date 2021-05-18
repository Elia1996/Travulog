#!/usr/bin/python3
import sys
import os
import re
import json

from moddata import *
#  GetInnerCommand(data_lines, lineno, key):
#  GetDeclarationForeach(block, inout, command, cmd2, lineno, indent):
#  GetPrefixSuffix(what, sequence, key, lineno):
#  SetSignalElaborationInstance(block_obj, siglist, inoutpar, after_equal, signal_elab, lineno):
#  GetCmdInstance(block_obj,  command, instance_name, lineno, indent_level):
#  GetInstanceForeach(block_obj, model_data, inout, lineno,indent):
#  GetOpUnroll(line_strip, start, end, op, sig, lineno, indent):
#  GetOpForeach(line_strip, block_obj, inout, op, sig, lineno, indent):
#  GetStringIndent( stringa, indent=1):
#  travulog class
#     __init__(sf, template_filename, template_params_filename, module_filename_dict = {},  module_prefix="", indent="        "):
#     SetModuleFilename(sf, block_id, md_obj):
#           Permette di settare l'oggetto moddata relativo all'id block_id che viene utilizzato all'interno del
#           travulog per indicare il blocco da usare
#     GetIndent(sf, indent_level=1):
#     GetElaboratedTemplate(sf,module_name, param_name):
#           Utilizza GetElaboratedTravulog per elaborare il file template del nuovo blocco e lo ritorna
#     GetElaboratedTemplateParams(sf,module_name, param_name):
#           Utilizza GetElaboratedTravulog per elaborare il file dei parametri settato in __init__ e lo ritorna
#     GetElaboratedTravulog(sf, module_name, param_name):
#           Elabora un file Travulog utilizzando le proprietà dei vari moduli settati con SetModuleFilename
#           ritornando il file trasformato.

def CompressLineSpaceTabs(line):
    return " ".join(line.strip().split()).strip()


def DeleteKeySplitLine(line, key):
    line2 = DeleteKey(line,key)
    return line2.split(" ")

def DeleteKey(line, key):
    line = CompressLineSpaceTabs(line)
    return line.replace(key,"").strip()

def CompressInstanceLine(line):
    line_no_space = CompressLineSpaceTabs(line)
    line1 = line_no_space.replace(".", " ").replace("(","#")
    line2 = re.sub(r'\)\W*,' , ' ' , line1)
    line2 = re.sub(r'\)\W*\)*' , ' ' , line2)
    line3 = RemoveComments(line2)
    line3 = line3.replace(" # ", "#")
    line_compress = CompressLineSpaceTabs(line3)
    return line_compress


def SplitInstanceLine(line):
    return CompressInstanceLine(line).split("#")


def GetInnerCommand(data_lines, lineno, key1, key2=""):
    """
     This function return all text between lineno and the first occurrence
     of key, data_lines is a list of lines
    """
    i=lineno+1
    command=""
    if key2 == "":
        while not key1 in data_lines[i]:
            command+=data_lines[i].strip() + "\n"
            i+=1
            if i > len(data_lines):
                print("ERROR at line %d end keyword %s not found" % lineno, key)
                exit(-1)
    else:
        while not ( key1 in data_lines[i] or key2 in data_lines[i]):
            command+=data_lines[i].strip() + "\n"
            i+=1
            if i > len(data_lines):
                print("ERROR at line %d end keyword %s not found" % lineno, key)
                exit(-1)
        command2=""
        if  key1 in data_lines[i]:
            while not key2 in data_lines[i]:
                command2+=data_lines[i].strip() + "\n"
                i+=1
                if i > len(data_lines):
                    print("ERROR at line %d end keyword %s not found" % lineno, key)
                    exit(-1)
        else:
            command2= command
            command=""

        return [command, command2, i+1]


    return [command,i+1]

def GetDeclarationForeach(block, inout, command, cmd2, lineno, indent):
    """
     This function create a declaration foreach IN, OUT or both of a block.
     Cycling along input or/and output SIGNAME and BITINIT are substituted in "command" stringa
     Considering the example:
     //// DECLARATION_FOREACH MAIN_MODULE INTERN NOT clk rst_n
     ////    logic [2:0]BITINIT SIGNAME_tr
     //// REPLACE
     block -> is the object of moddata (main module object)
     inout -> is the type of signal on which cycle (INTERN)
     command -> string in which replace elements (logic [2:0]BITINIT SIGNAME_tr)
     cmd2 -> is a dictionary with second command ({"NOT":["clk", "rst_n"]})
    """
    data=""
    if inout == "IN" or inout == "IN_OUT":
        for sig,bit_dict in zip(block.GetInputSigNamesList(), block.GetInputSigBitsList()):
            ok=1
            if "NOT" in cmd2.keys():
                if sig in cmd2["NOT"]:
                    ok=0
            if ok==1:
                data += indent
                bitdef = CreateBitsDefinition(bit_dict)
                data+= command.replace("INOUT","input").replace("SIGNAME",sig).replace("BITINIT",bitdef)

    if inout == "OUT" or inout == "IN_OUT":
        for sig,bit_dict in zip(block.GetOutputSigNamesList(), block.GetOutputSigBitsList()):
            ok=1
            if "NOT" in cmd2.keys():
                if sig in cmd2["NOT"]:
                    ok=0
            if ok==1:
                data += indent
                bitdef = CreateBitsDefinition(bit_dict)
                data+= command.replace("INOUT","output").replace("SIGNAME",sig).replace("BITINIT",bitdef)

    if inout == "INTERN":
        for sig,bit_dict in zip(block.GetInternSigNamesList(), block.GetInternSigBitsList()):
            ok=1
            if "NOT" in cmd2.keys():
                if sig in cmd2["NOT"]:
                    ok=0
            if ok==1:
                data += indent
                bitdef = CreateBitsDefinition(bit_dict)
                data+= command.replace("INOUT","output").replace("SIGNAME",sig).replace("BITINIT",bitdef)


    if inout != "OUT" and inout != "IN" and inout != "IN_OUT":
        print("ERROR line %d, INOUT variable can be only IN,OUT or IN_OUT" % lineno)

    data += "\n"
    return data

def GetPrefixSuffix(what, sequence, key, lineno):
    #############################################################################
    # This function analyze sequence list and it find prefix and suffix of key
    # the general format is "prefix key suffix", key can also don't exist, but
    # should be at least a word. We could have the following case:
    #   prefix key
    #   key suffix
    #   suffix
    #   prefix key suffix
    #############################################################################
    prefix=""
    suffix=""
    if what == key:
        if len(sequence) == 3: # we have prefix and suffix
            if sequence[1] == key:
                prefix = sequence[0]
                suffix = sequence[2]
            else:
                print("ERROR : line %d second argument of \"%s =\" should be %s " % lineno,key,key)
                exit(-1)
        elif len(sequence) == 2:
            if sequence[0] == key:
                suffix = sequence[1]
            elif sequence[1] == key:
                prefix = sequence[0]
            else:
                print("ERROR : line %d, when you give two argument first or second should be %s" % lineno,key)
                exit(-1)
        elif len(sequence) == 1 and sequence[0] != "IN" and sequence[0] != "OUT" and sequence[0] != "PARAM":
            prefix="UNIQUE"
            suffix = sequence[0]
        elif len(sequence) == 1:
            prefix=""
            suffix=""
        else:
            print("ERROR : line %d, you should said how to connect signals" % lineno)
            exit(-1)
    return [prefix, suffix]


def CheckInoutCorrectAfterEqualReplaceInout(cmd,inout, lineno):
    if inout != "IN" and inout != "OUT" and inout!="PARAM":
        print("ERROR line %d, IF without IN,OUT or PARAM keyword, cmd : %s"%(lineno,cmd))
        exit(-1)
    if inout == "IN":
        if "OUT" in inout or "PARAM" in inout:
            print("ERROR line %d, if you use %s before equal, you should use %s after equal to indicate signal"%(lineno,inout, inout))
            exit(-1)
    elif inout == "OUT":
        if "IN" in inout or "PARAM" in inout:
            print("ERROR line %d, if you use %s before equal, you should use %s after equal to indicate signal"%(lineno,inout, inout))
            exit(-1)
    else:
        if "IN" in inout or "OUT" in inout:
            print("ERROR line %d, if you use %s before equal, you should use %s after equal to indicate signal"%(lineno,inout, inout))
            exit(-1)
    
    return  cmd.replace(inout, "SIG")

def SplitBracket(stringa):
    str_split = stringa.replace("{","").replace("}","").split(",")
    str_split_correct = []
    for element in str_split:
        str_split_correct.append(element.replace(" ",""))

    return str_split_correct

def GetInstanceInfo(text, real_line_start):
    """ Return a dict containing all info of instance:
    {"module_name": str, 
     "instance_name": str, 
     "param_connections" : { "param" : "connected_param" , ... },
     "io_connections": { "signal": "connected_sig", ....},
     "indent_int" : int}

    """
    if type(text) == list:
        lines_l = text
    else:
        lines_l = text.split("\n")

    info_dict = {"module_name": "", "instance_name":"", "param_connections": {} , "io_connections": {}, "indent_int":0}

    line=""
    oldline = line
    start_line = 0
    search_blockname = True
    save_parameter = False
    save_io = False
    end_save = False
    connection_set = False

    real_lineno = real_line_start

    for line in lines_l:
        line= CompressLineSpaceTabs(line)

        if "#(" in line and search_blockname:
            current_line_indent = GetStringIndent(lines_l[real_lineno-real_line_start], 8)
            info_dict["indent_int"] = current_line_indent
            
            if len(line.split(" ")) > 1:
                if line.split(" ")[0] != "#(":
                    mod_name = line.split(" ")
                    search_blockname = False
                    save_parameter = True
                else:
                    print("ERROR in parsing, line %d"% real_lineno)
                    exit(-1)
            else:
                mod_name = oldline.split(" ")[0]
                info_dict["module_name"] = mod_name

                search_blockname = False
                save_parameter = True

        # We find the blockname witout
        elif "(" in line and search_blockname:
            if len(line) == 1:
                if len(oldline.split(" ")) == 2:
                    mod_name = oldline.split(" ")[0]
                    info_dict["instance_name"] = oldline.split(" ")[1]
                else:
                    print("ERROR while parsing line %d" % real_lineno)
                    exit(-1)
            else:
                if len(line.split(" ")) < 2:
                    print("ERROR line %d while parsing" % real_lineno)
                    exit(-1)
                mod_name = line.split(" ")[0]
                info_dict["instance_name"] = line.split(" ")[1].replace("(","")

            search_blockname = False
            save_io = True

            info_dict["module_name"] = mod_name

        # We save parameter connections
        elif "." in line and save_parameter:
            if re.findall("\)\W*,",line)!= [] or re.findall(r'\)\W*\)*', line)!=[]:
                if len(re.findall(r'\)\W*\)', line)) != 0:
                    save_parameter = False
                    save_io = True
                # We eliminate ( , ) and . from the line in order to have
                # only the name of the port and of the signal to connect
                line_param_list = SplitInstanceLine(line)
                if len(line_param_list) != 2:
                    print("ERROR in parser line %d, multiple instance on the same line not "
                        "implemented in  the parser 1" % real_lineno)
                    exit(-1)

                # We create a list of dict where the key is the name of the parameter
                # of module and the value is the connection do to, the dictionary is created because
                # the order of connection can be different, we then reordered the list of connection
                info_dict["param_connections"][line_param_list[0]] = line_param_list[1]

            else:
                print("ERROR line %d, multiple instance on the same line not implemented in"
                        " the parser 2" % real_lineno)
                exit(-1)

        # We save io connections
        elif (re.match("^\W+\..*", line)!= None or re.match("^\..*", line)!= None) and save_io:
            if re.findall("\)\W*,",line)!= [] or re.findall(r'\)\W*\)*', line)!=[]:
                # If we are in the last line of the declaration
                if len(re.findall(r'\)\W*\)\W*;', line)) != 0:
                    end_save = True
                # split line
                line_param_list = SplitInstanceLine(line)
                # Verify that there is only  one declaration for line
                if len(line_param_list) != 2:
                    print("ERROR in parser line %d, multiple instance on the same line not "
                        "implemented in  the parser 3" % real_lineno)
                    exit(-1)
                info_dict["io_connections"][line_param_list[0]] = line_param_list[1]

            else:
                print("ERROR line %d, multiple instance on the same line not implemented in"
                        " the parser 4, %s " % (real_lineno, line))
                exit(-1)

        elif ")" in line and not ";" in line:
            if len(SplitInstanceLine(line)) == 1:
                if len(line) == 1:
                    real_lineno +=1
                    line = CompressLineSpaceTabs(lines_l[real_lineno-real_line_start])
                    info_dict["instance_name"] = line.split(" ")[0].replace("(","")
                else:
                    info_dict["instance_name"] = line.replace(")","").replace("(","")
            else:
                if line.split(" ")[0] == ")":
                    info_dict["instance_name"] = line.split(" ")[1].replace("(","")
                else:
                    info_dict["instance_name"] = line.split(" ")[0].replace(")","").replace("(","")

            save_parameter = False
            save_io = True

        elif "(" in line and len(CompressLineSpaceTabs(line)) == 1:
            save_parameter = False
            save_io = True

        elif re.findall(r'\)\W*;', line) != []:
            end_save = True

        oldline = line
        real_lineno +=1

    return info_dict


def InstanceCommandParse(cmd_line, lineno, key = "////"):
    """ Parse a connection string like:
    IF clk rst_n IN = { IN_tr, IN_tr, tr_IN[0]}
    Creating a dictionary like:
    ["IN" , { "siglist":[ "clk", "rst_n"], "pattern": "{ PRECONSIG_trSUFCON, PRECONSIG_trSUFCON, PRECONtr_SIG[0]SUFCON }" ]
    The you should replace PRECON and SUFCON with the prefix and the suffix of the connections and you
    should replace SIG with the correct sig.
    cmd_line -> line of command
    lineno -> number of line in order to correctly prompt errors
    """
    if not "IN" in cmd_line and not "OUT" in cmd_line and not "PARAM" in cmd_line and not "=" in cmd_line:
        print("ERROR line %d, IF without IN,OUT or PARAM keyword, line1: %s"%(lineno, cmd_line))
        exit(-1)

    cmd_line = DeleteKey(cmd_line, key)
    # ex: IF clk rst_n IN = { IN_tr, IN_tr, tr_IN[0]}
    before_equal = cmd_line.split("=")[0].strip().split(" ") # IF clk rst_n IN
    after_equal = cmd_line.split("=")[1].strip()  # { IN_tr, IN_tr, tr_IN[0] }
    #print("after_equal: -"+cmd_line+"-")
    
    inout = before_equal[-1]
    if inout != "IN" and inout != "OUT" and inout!="PARAM":
        print("ERROR line %d, IF without IN,OUT or PARAM keyword, line2 \"%s\""%(lineno,cmd_line))
        exit(-1)

    ######  IF parsing
    command_list = []
    if len(before_equal) > 1 and before_equal[0] != "IF": # ex: "IFF clk IN"  here IFF is wrong
        print("ERROR line %d, before = you should only indicate IN/OUT/PARAM and optionally use \"IF list\""%lineno)
        exit(-1)
    if before_equal[0] == "IF" and len(before_equal)<3: # ex: "IF IN" here the string leak of sig list 
        print("ERROR line %d, if you use IF you should indicate at least a signal"%lineno)
        exit(-1)

    if before_equal[0] == "IF":
        command_list += before_equal[1:-1] # clk rst_n

    ######  CONNECTION parsing
    # cmd_str is a string that will be used as template to create the connection
    # general form is:
    #  PRECON PREFIX SIG SUFFIX SUFCON
    # PRECON and SUFCON are prefix and suffix that are present in the instance
    # connection, for example for the connection .addr (addr[0]) we have 
    # PRECON="" and SUFCON="[0]", SUFFIX and PREFIX are added by the travulog command
    # and placed near to the signal name
    # If for example we have the command { IN_tr, IN_tr, tr_IN[0] }, cmd_str became
    # { PRECONSIG_trSUFCON, PRECONSIG_trSUFCON, PRECONtr_SIG[0]SUFCON }
    cmd_str = ""
    if "," in after_equal:
        if not "{" in after_equal or not "}" in after_equal:
            print("ERROR line %d, after equal you can use {sig1, sig2, ...} but you forgot \"{ or }\""%lineno)       
            exit(-1)
        
        after_equal = " ".join(after_equal.replace(","," ").replace("{","").replace("}","").strip().split())
        after_equal = " ".join(CheckInoutCorrectAfterEqualReplaceInout(after_equal, inout, lineno).split())
        # Create cmd_str
        cmd_str += "{ "
        end_str = " , "
        cnt=0
        for sig in after_equal.split(" "):
            if cnt == len(after_equal.split(" "))-1:
                end_str = " }"
            cmd_str += "PRECON" + sig + "SUFCON " + end_str
            cnt+=1


    elif len(after_equal.split(" ")) != 1:
        print("ERROR line %d, after equal you can use {sig1, sig2 , ... } or set a single signal with or without prefix and suffix, like : IN=prefix_IN_suffix, you write %s"%(lineno, after_equal))       
        exit(-1)
    else:
        after_equal = CheckInoutCorrectAfterEqualReplaceInout(after_equal, inout, lineno)
        cmd_str += "PRECON" + after_equal + "SUFCON"

    return [inout , {"siglist":command_list,"pattern":cmd_str}]

def GetCmdElab(block_obj, command, lineno, HTKEY = "////"):
    """ Return a dictionary that contain connection trasformation
    Basic structure of this dictionary is {"IN":[], "OUT":[], "PARAM":[]}

    """
    # I divide line and delete the htravulog key
    cmd_lines = []
    if type(command) == list:
        for cm in command:
            cmd_lines.append(DeleteKey(cm, HTKEY))
    else:
        cmd_line_old=command.strip().split("\n")
        for cm in cmd_line_old:
            cmd_lines.append(DeleteKey(cm, HTKEY))

    ### Creation of the dictionary with pattern to apply at each port
    cmd_dict = {"IN":[], "OUT":[], "PARAM":[]}
    for cmd_line in cmd_lines:
        if cmd_line != "":
            [inout, connection_dict] = InstanceCommandParse(cmd_line, lineno, HTKEY)
            cmd_dict[inout].append(connection_dict)

    return cmd_dict

def GetBitNumber(bit_dict, index, lineno):
    if index != 0 and index != 1:
        print("ERROR line %d, you can't use array, only \"logic [][] signame\" are valid"%lineno)
        exit(-1)
    if index == 0:
        return int(abs(int(bit_dict["N0UP"])-int(bit_dict["N0DW"]))+1)
    if index == 1:
        return int(abs(int(bit_dict["N1UP"])-int(bit_dict["N1DW"]))+1)

def GetCmdInstance(block_obj,  command, instance_name, lineno, indent_level, upper_block_obj = None, old_connection_dict=None , HTKEY = "////"):
    block_obj = SetObjConnection(block_obj,  command, lineno, upper_block_obj, old_connection_dict , HTKEY)
    data = block_obj.GetInstance(instance_name, indent_level)
    return data


def SetObjConnection(block_obj,  command, lineno, upper_block_obj = None, old_connection_dict=None , HTKEY = "////"):
    """ This function set input and output connection in the moddata obj called block_obj.
    Arguments are:
    block_obj -> moddata obj 
    command -> It is a string containing the travulog or htravulog code that define the pattern of connection,
            like "IF MAIN_MODULE_IN IN = {IN , IN , IN }
        ////          IF NEW_IN IN = IN[MAIN_MODULE_PARAM_ID_PRCODE] 
        ////          IN = IN_tr
        ////          IF NEW_OUT OUT = OUT[MAIN_MODULE_PARAM_ID_PRCODE]
        ////          OUT = OUT_tr"
    lineno -> line used for errors
    upper_block_obj -> Supponing to have a main module called if_stage and a submodule called if_pipeline, now if
        we have changed some internal signals in if_stage that are used to connect if_pipeline, or the if_pipeline
        input change dimension, we shoul correctly connect this changed signal. In this function is supported only
        the case in which if_pipeline change dimension of output, if for example a input is triplicated, the corresponding
        intern signal of the if_stage is connected three time in order to fill the if_pipeline input.
    old_connection_dict -> Is a dictionary where each IO of the module is connected to a signal, for example if the instance
        has a line like: ".branch_addr_i     ( {branch_addr_n[31:1], 1'b0} )," old_connection_dict will have an element like
        { "branch_addr_i": "{branch_addr_n[31:1], 1'b0"}
    """
    cmd_dict = GetCmdElab(block_obj, command, lineno,  HTKEY) 
    ### Creation of the connection signals
    # INPUT
    port_connection_list= {"IN":[], "OUT":[], "PARAM":[]}
    

    # FOR1 Cycle on input signal of instance 
    for sig_tc_name, sig_tc_bit, sig_tc_type in zip(block_obj.GetAllIoSigName(), block_obj.GetAllIoSigBits(), block_obj.GetAllIoSigType()):
        # FOR2 cycle on if dict {"siglist":command_list,"pattern":cmd_str]} using the type of signal to connect
        for if_dict_of_sig in cmd_dict[sig_tc_type]:
            # IF1  If the siglist is empty or it contain the signal name, we create connection as pattern said
            if if_dict_of_sig["siglist"] == [] or  sig_tc_name in if_dict_of_sig["siglist"]:
                # IF2  If the upper block is given we use previous connection
                if upper_block_obj != None and old_connection_dict!= None:
                    # We cycle in upper block signals to find what signal we should connect
                    # if this signal is connected partially like:
                    #     .branch_addr_i     ( {branch_addr_n[31:1], 1'b0} ),
                    # We should find if branch_addr_i is changed in an array like [2:0][31:0], in this case
                    # we should triplicate the connection like:
                    #     .branch_addr_i     ( {branch_addr_n[2][31:1], 1'b0},{branch_addr_n[1][31:1], 1'b0},{branch_addr_n[0][31:1],1'b0}),
                    # old_connection_dict contain all connection like {branch_addr_n[31:1], 1'b0} 
                    # 
                    for sig_name, sig_bit in zip(upper_block_obj.GetAllSigName(), upper_block_obj.GetAllSigBits()):
                        if sig_name in old_connection_dict[sig_tc_name]:
                            # If there is a simply connection like ".branch_addr_i (branch_addr)" we apply only the pattern
                            # verifying that the bits are the same
                            if sig_name == old_connection_dict[sig_tc_name]:
                                newsig1 = if_dict_of_sig["pattern"].replace("SIG",sig_name + "INDEX")
                                newsig1 = newsig1.replace("PRECON", "")
                                newsig1 = newsig1.replace("SUFCON","")
                            # If the connection is complex like ".branch_addr_i ( {branch_addr_n[31:1], 1'b0} )," we should
                            # verify the number of bits and apply suffix correctly
                            else:
                                sig_split = old_connection_dict[sig_tc_name].split(sig_name) # [ '{' , '[31:1], 1'b0}' ]
                                newsig1 = if_dict_of_sig["pattern"].replace("SIG",sig_name+"INDEX")
                                newsig1 = newsig1.replace("PRECON", sig_split[0])
                                newsig1 = newsig1.replace("SUFCON",sig_split[1])
                        
                            if sig_bit != sig_tc_bit:
                                # If the first number of bit is equal we connect the signal like:
                                #  .branch_addr_i ( { branch_addr_n, branch_addr_n, branch_addr_n } )
                                correct=False
                                if GetBitNumber(sig_tc_bit,1,lineno) != 1 and GetBitNumber(sig_bit,1,lineno) == 1:
                                    bitn_tc = GetBitNumber(sig_tc_bit,1,lineno) 
                                    bitn = GetBitNumber(sig_bit,1,lineno)
                                    correct = True
                                elif GetBitNumber(sig_tc_bit,1,lineno) == 1 and GetBitNumber(sig_bit,1,lineno) == 1:
                                    bitn_tc = GetBitNumber(sig_tc_bit,0,lineno) 
                                    bitn = GetBitNumber(sig_bit,0,lineno)
                                    correct = True

                                if correct :
                                    if bitn_tc > bitn and bitn_tc % bitn == 0:
                                        newsig = "{"
                                        for i in range(bitn_tc//bitn-1, 0, -1):
                                            newsig += newsig1.replace("INDEX","["+str(i)+"]") + " , "
                                        newsig += newsig1.replace("INDEX","[0]") + "}"
                                    else:
                                        print("ERROR line %d, program can't manage the connection of sig %s [%s:%s][%s:%s]"
                                            "with sig %s [%s:%s][%s:%s] number of bits 1 are not multiple (%d,%d)." %( lineno,
                                            sig_name , sig_bit["N1UP"], sig_bit["N1DW"], sig_bit["N0UP"], sig_bit["N0DW"],
                                            sig_tc_name, sig_tc_bit["N1UP"],sig_tc_bit["N1DW"], sig_tc_bit["N0UP"], sig_tc_bit["N0DW"],
                                            bitn_tc, bitn)
                                            )
                                        exit(-1)
                                else:
                                    print("ERROR line %d, signal %s is a [%s:%s][%s:%s] sig while signal %s is a "
                                        "[%s:%s][%s:%s] sig, verify connections!" 
                                         % (lineno,
                                        sig_name , sig_bit["N1UP"], sig_bit["N1DW"], sig_bit["N0UP"], sig_bit["N0DW"],
                                        sig_tc_name, sig_tc_bit["N1UP"],sig_tc_bit["N1DW"], sig_tc_bit["N0UP"], sig_tc_bit["N0DW"])
                                        )
                                    exit(-1)
                            else:
                                newsig = newsig1.replace("INDEX","")
                            
                        # If sig_name isn't in old_connection_dict
                        else:
                            newsig1 = if_dict_of_sig["pattern"].replace("SIG",sig_tc_name )
                            newsig1 = newsig1.replace("PRECON", "")
                            newsig1 = newsig1.replace("SUFCON","")
                            newsig = newsig1
                    # END FOR
                # END IF2 If we don't have upper object
                else:
                    newsig = if_dict_of_sig["pattern"].replace("SIG",sig_tc_name).replace("PRECON", "").replace("SUFCON","")

                port_connection_list[sig_tc_type].append(newsig)
                break
            # END IF1
        # END FOR2
        else: 
            port_connection_list[sig_tc_type].append(sig_tc_name)

    # END FOR1
            
    block_obj.SetInputPortConnections(port_connection_list["IN"])
    block_obj.SetOutputPortConnections(port_connection_list["OUT"])

    return block_obj



def GetInstanceForeach(block_obj, model_data, inout, lineno,indent):
    """
     Starting from a verilog code with some variable this function return
     a new code with variable substituted.
     SIGNAME -> name of the signal to vote
     INDEX -> error correction and detection are saved as vectors, for these
               reason each voter will have a number used to address these vectors
     BITNUMBER -> number of bits of signal to vote
     VOTER_NAME -> name of the instance of the voter
    """
    names=[]
    bits=[]
    if inout == "IN" or inout == "IN_OUT":
        names = block_obj.GetInputSigNamesList()
        bits = block_obj.GetInputSigBitsList()
    if inout == "OUT" or inout == "IN_OUT":
        names += block_obj.GetOutputSigNamesList()
        bits += block_obj.GetOutputSigBitsList()
    if inout == "INTERN":
        names = block_obj.GetInternSigNamesList()
        bits = block_obj.GetInternSigBitsList()

    if inout!="IN" and inout != "OUT" and inout !="IN_OUT" and inout != "INTERN":
        print("ERROR at line %d, %s is wrong, only IN, OUT, IN_OUT or INTERN can be used "%lineno, inout)
        exit(-1)
   
    index=0
    instance = ""
    for sig,bit_dict in zip(names, bits):
        data=model_data
        # Substitute signal name
        data = data.replace("SIGNAME",sig)
        # Substitute the index of output for error detection and correction signals
        data = data.replace("INDEX", str(index))
        if bit_dict["N0UP"] == "1" and bit_dict["N0DW"] == "0":
            data = data.replace("BITNUMBER","1")
        else:
            data = data.replace("BITNUMBER",str(int(bit_dict["N0UP"])+1))

        ndata=""
        for line in data.split("\n"):
            if "." in line:
                ndata = ndata + indent + "         "+ line + "\n"
            else:
                ndata = ndata + indent + line + "\n"
        instance += ndata
        index += 1

    return instance

def GetOpUnroll(line_strip, start, end, op, sig, lineno, indent):
    """
    """
    if start > end or start==end:
        print("Error line %d, start (%d) should be less then end (%d)"%lineno,start,end)
        exit(-1)
    unroll=indent
    words=line_strip.split(" ")
    indent_word = ""
    i=0
    while i < len(words):
        if words[i] == "OP_UNROLL":
            i+=5
            cnt=int(start)
            indent_word = len(unroll.strip())*" "
            operation= " " +sig + "["+str(cnt)+"]\n"
            cnt+=1
            while cnt < int(end)-1:
                operation += indent + indent_word+ op + " " + sig + "["+str(cnt)+"]\n"
                cnt+=1
            operation += indent + indent_word+ op + " " + sig + "["+str(cnt)+"];\n"
            unroll += operation

        else:
            unroll += words[i] + " "
        i+=1

    return unroll

def GetOpForeach(line_strip, block_obj, inout, op, sig, lineno, indent):
    unroll=indent
    words=line_strip.split(" ")
    indent_word = ""
    i=0
    while i < len(words):
        if words[i] == "OP_FOREACH":
            i+=4
            names=[]
            bits=[]
            if inout == "IN" or inout == "IN_OUT":
                names = block_obj.GetInputSigNamesList()
                bits = block_obj.GetInputSigBitsList()
            if inout == "OUT" or inout == "IN_OUT":
                names += block_obj.GetOutputSigNamesList()
                bits += block_obj.GetOutputSigBitsList()
            if inout!="IN" and inout != "OUT" and inout !="IN_OUT":
                print("ERROR at line %d, %s is wrong, only IN, OUT or IN_OUT can be used "%lineno, inout)
                exit(-1)
            indent_word = len(unroll.strip())*" "
            if op == "//" :
                if len(unroll.strip())>=2:
                    indent_word = (len(unroll.strip())-2)*" "
                else:
                    indent_word = ""
                
            indent_word = indent + indent_word
            end_str="\n"
            if len(sig.replace("SIGNAME",names[0]))*len(names) < 50:
                end_str = ""
                indent_word = ""
            
            operation= " " + sig.replace("SIGNAME",names[0]).replace("INDEX","0") + end_str
            cnt=1
            while cnt < len(names)-1:
                operation += indent_word+ op + " " + sig.replace("SIGNAME",names[cnt]).replace("INDEX",str(cnt)) + end_str
                cnt+=1
            operation += indent_word+ op + " " + sig.replace("SIGNAME",names[cnt]).replace("INDEX",str(cnt)) 
            unroll += operation

        else:
            unroll += words[i] + " "
        i+=1
    
    unroll += "\n"

    return unroll


def GetStringIndent( stringa, indent=1):
    #######################################################################
    # Find the current indentation of "stringa", this
    # function return the number of space before the first letter
    #######################################################################
    endindent=0
    indent_cnt=0
    for letter in stringa:
        if not endindent:
            if letter==" ":
               indent_cnt+=1
            else:
                return indent_cnt//indent


class travulog:
    def __init__(sf, template_filename, template_params_filename, module_filename_dict = {},  module_prefix="", indent="        "):
        """ 
        module_filename_dict -> is a dict like { "BLOCK": "path/to/module1.sv", "BLOCK2":"path/to/module2.sv" }
                    the name BLOCK and BLOCK2 can be used inside travulog to refer to that block data
        template_filename -> filename of the template to use for the creation of new blocks, this template is 
                    writte in verilog with travulog insertion
        package_filename -> package filename, written as template_filename but containing only parameter definition
        indent -> indent unit (tab)
        """
        sf.mod_fname_dict = module_filename_dict
        sf.indent = indent
        sf.template_params_fname = template_params_filename
        sf.template_fname = template_filename
        sf.filename = sf.template_fname
        sf.mod_prefix= module_prefix

        # Find module data using moddata class
        sf.mod_obj_dict = {}
        if module_filename_dict != {}:
            for mod_fname_name, mod_fname_filename in zip(module_filename_dict.keys(),module_filename_dict.values()):
                sf.mod_obj_dict[mod_fname_name] = moddata(mod_fname_filename, sf.mod_prefix)
                sf.mod_obj_dict[mod_fname_name].Analyze()

    ######################################################################################################
    # SET Functions
    ######################################################################################################
    def SetModuleFilename(sf, block_id, md_obj):
        sf.mod_obj_dict[block_id] = md_obj

    ######################################################################################################
    # GET Functions
    ######################################################################################################

    def GetIndent(sf, indent_level=1):
        return sf.indent*indent_level


    def GetElaboratedTemplate(sf,module_name, param_name):
        sf.filename = sf.template_fname
        return sf.GetElaboratedTravulog(module_name, param_name)

    def GetElaboratedTemplateParams(sf,module_name, param_name):
        if sf.template_params_fname == "":
            return 1
        sf.filename = sf.template_params_fname
        return sf.GetElaboratedTravulog(module_name, param_name)

    def GetElaboratedTravulog(sf, module_name, param_name):
        """
         This function start from a template file that create a FT structure of a non 
         FT block, in this file will be many uppercase variable that should be substitute by 
         block of autogenerated code. This autogenerated code depends by arguments of this function
         These are parameter that wil be substitute:
         Global variable , this variable are substitute before elaboration in all file
        -- MODULE_NAME -> Name of the module
        -- PARAM_NAME -> there are some parameters used in verilog to change FT behaviour
                           this parameter is the base name of these parameters
        -- block_name_MODNAME -> name of the block
        
         Elaboration blocks, elements in this block will be cloned for all in or out signal
        -- PARAMETER_DECLARATION block_name -> declare the same parameter of block_name module
        -- DECLARATION_FOREACH block_name inout    
               declaration_command
           END_DECLARATION -> cycle on block_name input (if inout=IN) or output 
                           (if inout=OUT) or both (if inout=IN_OUT) and substitute follow variable:
                           INOUT -> if the signal is an input INOUT="input", if it is an output INOUT="output"
                           BITINIT -> if the signal has only a bit BITINIT="" otherwhise BITINIT="[BITNUMBER-1:0]"
                           SIGNAME -> It is substituted with signal name
        -- INSTANCE block_name
               PARAM = 
               IN = IN_string   
               OUT= OUT_string
           END_INSTANCE -> create an instance of block_name connecting input/output signals adding string, 
               for example:
                   INSTANCE BLOCK
                       PARAM=PARAM
                       IN=IN[0]
                       OUT = OUT_to_vote[i]
                   END_INSTANCE
               Generate:
                   cv32e40p_compressed_decoder #(FPU) compressed_decoder
                   (
                       .instr_i(instr_i[0]),
                       .instr_o(instr_o_to_vote[i]),
                       .is_compressed_o(is_compressed_o_to_vote[i]),
                       .illegal_instr_o(illegal_instr_o_to_vote[i])
                   );
        
        -- INSTANCE_FOREACH block_name inout
               instance_template
           END_INSTANCE  -> This command cycle on input or output of block and substitute
                       variable in instance_template string in order to create instance of some
                       block connected to input, output or both of block_name block.
                       Variable can be:
                           BITNUMBER -> number of bit of the signal to connect
                           INDEX -> index of cycle
                           SIGNAME -> name of the signal
           
        -- OR_UNROLL start end operation signame -> this command unroll a reduction operation in order
                           to have better representation in schematic during complation.
                           For example:
                               assign err_detected_o = OP_UNROLL 0 3 | err_detected ;
                           Generate:
                               assign err_detected_o =   err_detected[0] 
                                                       | err_detected[1] 
                                                       | err_detected[2];
        -- OP_FOREACH block_name inout operation expression -> apply an operation between each input
                       or output of block_name block. For example:
                           assign block_err_detected[m] = OP_FOREACH BLOCK OUT | SIGNAME_block_err[m] ;
                       Generate:
                           assign block_err_detected[m] =   instr_o_block_err[m]
                                                          | illegal_instr_o_block_err[m]
                                                          | is_compressed_o_block_err[m];
           
        """

        #print(sf.mod_obj_dict["BLOCK"].GetInputSigNamesList())
        fp = open(sf.filename,"r") 
        data_orig=fp.read()
        tab="        "
        data_orig=data_orig.replace("\t",tab)


        ####  Substitution of constant
        data = data_orig.replace("MODULE_NAME",module_name)
        data = data.replace("PARAM_NAME", param_name)
        data = data.replace("MODULE_INDEX", param_name)
        # substitute all BLOCK_MODNAME with corrsipetive module name
        for mod_ID,mod_obj in zip(sf.mod_obj_dict.keys(), sf.mod_obj_dict.values()):
            data = data.replace(mod_ID+"_MODNAME", mod_obj.GetModuleNameNoPrefix())
            data = data.replace("SIG_NUM-"+mod_ID +"-OUT", str(len(mod_obj.GetOutputSigNamesList())-1))
            data = data.replace("SIG_NUM-"+mod_ID +"-IN", str(len(mod_obj.GetInputSigNamesList())-1))

        data_line = data.split("\n")

        data_elab=""
        lineno=0
        linemax=len(data_line)

        # Elaboration cycle
        while lineno < linemax:
            line=data_line[lineno]
            indent_int= GetStringIndent(line) 
            line_indent = 1
            if type(indent_int)== int and indent_int > 0:
                indent_string = " "*(indent_int-1)
                line_indent  = len(indent_string.split(sf.indent))
            line_strip = line.strip()
            line_strip_split = line_strip.split(" ")

            # Parameter declaration
            if "PARAMETER_DECLARATION" in line_strip:
                if len(line_strip_split) == 2:
                    # get the dictionary of info of corresponding block
                    block_obj = sf.mod_obj_dict[line_strip_split[1]]
                    data_elab += block_obj.GetParameterDeclaration(0)
                else:
                    print("ERROR! PARAMETER_DECLARATION at line %d need "
                            "the name of block to copy parameter" % lineno)
                    exit(-1)

            elif "DECLARATION_FOREACH" in line_strip:
                # DECLARATION_FOREACH BLOCK IN_OUT
                #    INOUT logic [2:0]BITINIT SIGNAME,
                # END_DECLARATION_FOREACH

                if len(line_strip_split) >= 3:
                    block_obj = sf.mod_obj_dict[line_strip_split[1]]
                    inout=line_strip_split[2]

                    if len(line_strip_split) > 4:
                        cmd2 = {line_strip_split[3]: line_strip_split[4:]}
                    
                    [command, lineno]= GetInnerCommand(data_line, lineno, "END_DECLARATION_FOREACH")
                    data_elab += GetDeclarationForeach(block_obj, inout, \
                            command, cmd2, lineno, line_indent*sf.indent)
                else:
                    print("ERROR! DECLARATION_FOREACH at line %d needs"
                        "block name and IN/OUT/IN_OUT option" % lineno)
                    print("LINE: %s" % line_strip_split)
                    exit(-1)

            elif "INSTANCE " in line_strip:
                # INSTANCE BLOCK BLOCK_MODNAME_triplicated
                #         PARAM=PARAM
                #         IN = IN [i]
                #         OUT = OUT _to_vote[i]
                # END_INSTANCE
                if len(line_strip_split) == 3:
                    block_obj = sf.mod_obj_dict[line_strip_split[1]]
                    instance_name = line_strip_split[2]
                    [command, lineno]= GetInnerCommand(data_line, lineno, "END_INSTANCE")
                    #iprint(json.dumps(block,indent=4))
                    data_elab += GetCmdInstance(block_obj,  command, instance_name ,lineno, line_indent)
                    lineno-=1
                else:
                    print("ERROR! INSTANCE at line %d needs block name and instance name" % lineno)
                    exit(-1)

            elif "INSTANCE_FOREACH" in line_strip:
                # INSTANCE_FOREACH BLOCK OUT
                #         // Voter for TOVOTE signal, triple voter if
                #         // CDEC_TOUT[INDEX] == 1
                #         cv32e40p_conf_voter
                #         #(
                #                 .L1(BITNUMBER),
                #                 .TOUT(CDEC_TOUT[INDEX])
                #         ) voter_SIGNAME_INDEX
                #         (
                #                 .to_vote_i( SIGNAME_to_vote ),
                #                 .voted_o( SIGNAME),
                #                 .block_err_o( SIGNAME_block_err),
                #                 .broken_block_i(is_broken_o),
                #                 .err_detected_o(err_detected[INDEX]),
                #                 .err_corrected_o(err_corrected[INDEX])
                #         );
                # END_INSTANCE_FOREACH
                if len(line_strip_split) == 3:
                    block_obj = sf.mod_obj_dict[line_strip_split[1]]
                    inout = line_strip_split[2]
                    [command, lineno]= GetInnerCommand(data_line, lineno, "END_INSTANCE_FOREACH")
                    data_elab += GetInstanceForeach(block_obj,  command, inout, lineno, indent_int*" ")
                    lineno -=1 
                else:
                    print("ERROR! INSTANCE_FOREACH at line %d needs block name and inout parameter" % lineno)
                    exit(-1)    

            elif "OP_UNROLL" in line_strip:
                # assign err_detected_o = OP_UNROLL 3 | err_detected ;
                cmd = line_strip.split("=")[1].strip()
                cmd_split = cmd.split(" ")
                if len(cmd_split) > 5:
                    start=cmd_split[1]
                    end=cmd_split[2]
                    op=cmd_split[3]
                    sig=cmd_split[4]
                    data_elab += GetOpUnroll(line_strip, start, end, op, sig, lineno, indent_int*" ")
                else:
                    print("ERROR! OP_UNROLL at line %d needs block name and instance name" % lineno)
                    exit(-1) 

            elif "OP_FOREACH" in line_strip:
                # assign err_detected_o = OP_UNROLL 3 | err_detected ;
                i=0
                while i< len(line_strip_split):
                    if line_strip_split[i] == "OP_FOREACH":
                        if i+4 < len(line_strip_split):
                            cmd = line_strip_split[i:i+5]

                            i+=4
                        else:
                            print("ERROR! OP_FOREACH at line %d, some arguments are missing '%s'" % (lineno,line_strip))
                            exit(-1)
                    i+=1

                block_obj = sf.mod_obj_dict[cmd[1]]
                inout=cmd[2]
                op=cmd[3]
                sig=cmd[4]
                data_elab += GetOpForeach(line_strip, block_obj, inout, op, sig, lineno, indent_int*" ")


            else:
                data_elab+=line + "\n"
                
            lineno+=1

        return data_elab

filename_template="/media/tesla/Storage/Data/Scrivania/AllProject/Fare/Tesi/Esecuzione_tesi/cv32e40p_ft_tests/FTGenerator/ft_template.sv"
filename_block="/media/tesla/Storage/Data/Scrivania/AllProject/Fare/Tesi/Esecuzione_tesi/cv32e40p/rtl/cv32e40p_prefetch_buffer.sv"

def testGetElaboratedTravulog(filename_template, filename_block):
    module_filename_dict =  {"BLOCK": filename_block}
    template_filename = filename_template
    package_filename = ""
    tv = travulog( template_filename, package_filename, {}, module_prefix="cv32e40p_")
    print(tv.GetElaboratedTravulog("ciccio","VFDJ"))

#testGetElaboratedTravulog(filename_template,filename_block)





