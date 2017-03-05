/*!
 * AutoBuddy JavaScript Library v0.1
 * 

 * Copyright 2015 François Wautier
 * Released under the MIT license
 *
 * Date: 2015-08-16
 *       2016-12-05   Updated to reflect the changes in message structure. 
 *       2017-01      Updated to use Buddyguilib and added "icon status" support
 *       2017-02      Lots of changes. Dupport for configuration added. Cleaned naming
 ^                    
*/

var colourSchemes = [340,300,270,220] //hue 
var maxchild = 12;
var childstep = 4;
var zoneById={};
var deviceById={};
var nznametmpl = "New Zone "; /* New Zone name template */

/*
* Some utility functions
* This one is for indenting the options to reflect
* structure.
*/
String.prototype.repeat = function(count) {
    if (count < 1) return '';
    var result = '', pattern = this.valueOf();
    while (count > 1) {
      if (count & 1) result += pattern;
      count >>>= 1, pattern += pattern;
    }
    return result + pattern;
  };

function generate_bg_class() {
    var cssstr = "<style>\n.bu-layer-colour-0-0 { border-bottom-color: hsl(11,80%,60%); border-right-color: hsl(11,80%,60%);}\n";
    
    for (var i=0; i < colourSchemes.length; i++) {
        var hue=colourSchemes[i];
        var sat=80;
        var light=40;
        var step=5; //60 / 12
        for (var k=0; k < childstep; k++) {
            var cstring="hsl("+hue+","+sat+"%,"+light+"%)";
            cssstr+=".bu-layer-colour-"+(i+1)+"-"+k+" {border-bottom-color: "+cstring+"; border-right-color: "+cstring+";}\n";
            sat-=step;
            light+=step;
        }
    };

    $('html > head').append(cssstr);
}

function get_dict_keys(val) {
    if ($.isArray(val)) {
        return "&lt;list&gt;"
    }
    if ($.isEmptyObject(val)) {
        return ""
    }
    if (typeof val == "string") {
        return ""
    }
    var resu=[]
    $.each(val, function(pre,ival) {
        var tmp=get_dict_keys(ival);
        if ($.isArray(tmp)) {
            $.each(tmp, function (idx,strval) {
                resu.push(pre+"::"+strval)
            })
        } else if (tmp =="") {
            resu.push(pre)
        } else {
            resu.push(pre+"::"+tmp)
        }
    })
    return Array.from(new Set(resu));
//     return $.grep(resu, function(el, index) {
//         return index === $.inArray(el, array);
}

function set_cookie(key, value) {
    var expires = new Date();
    expires.setTime(expires.getTime() + (30 * 24 * 60 * 60 * 1000));
    document.cookie = key + '=' + value + ';expires=' + expires.toUTCString();
}

function get_cookie(key) {
    var keyValue = document.cookie.match('(^|;) ?' + key + '=([^;]*)(;|$)');
    return keyValue ? keyValue[2] : null;
}
 
function logout() {
    document.cookie = "buddyuser=; expires=Thu, 01 Jan 1970 00:00:01 GMT;";
    document.cookie = "buddypass=; expires=Thu, 01 Jan 1970 00:00:01 GMT;";
    location.reload()
}
 
function show_about () {
    var msg="<ul class=\"nav nav-tabs\">"
    var tabmsg = "<div id=\"about-tab-content\" class=\"tab-content\">";
    var active = " active";
    var haslic = false;
    var keylist = [];
    
    $.each(abouttext, function(key,val) {
        if (key=="License") {
            haslic=true;
        } else {
            if ( key != "AutoBuddy") {
                keylist.push(key);
            }
        }
    })
    keylist.sort();
    if ( haslic ) {
        keylist.push("License");
    }
    keylist.unshift("AutoBuddy");
    $.each(keylist,function (idx,key) {
        var val = abouttext[key];
        msg+="<li role=\"presentation\" class=\"bu-commandtab"+active+"\"><a href=\"#bu-about-"+key+"\"  data-toggle=\"tab\">"+key+"</a></li>";
        tabmsg+="<div class=\"tab-pane bu-commandpanel"+ active+"\" id=\"bu-about-"+key+"\">";
        tabmsg+=val;
        tabmsg+="</div>"
        active="";
    })
    msg+="</ul>"
                        
    bootbox.dialog({
        title: "<img src=\"/images/AutoBuddy-logo.svg\" width=\"30\" height=\"30\"/> About AutoBuddy <span class=\"pull-right bu-copyright\">&copy; 2015 Fran&ccedil;ois Wautier</span>",
        message:msg+tabmsg,
        buttons: {
            close: {
                label: "Close",
                className: "btn-close",
                callback: function () {
                    //$("#"+oname+"-power").destroy();
                    //return false;
                }
            }
        }
    });
}

function change_password () {
    var msg="<form class=\"form-ch-password\">"
    msg+="<div class=\"form-group\"><label for=\"opasswd\">Old Password</label><input class=\"form-control\" type=\"password\" name=\"oldPassword\" id=\"opasswd\" /></div>"
    msg+="<div class=\"form-group\"><label for=\"npasswd\">New Password</label><input class=\"form-control\" type=\"password\" name=\"mewPassword\" id=\"npasswd\" />"
    msg+="<label for=\"vpasswd\">Verify</label><input class=\"form-control\" type=\"password\" name=\"verPassword\" id=\"vpasswd\" /></div>"
    msg+="</form>"
                        
    bootbox.dialog({
        title: "Change Password",
        message:msg,
        buttons: {
            close: {
                label: "Cancel",
                className: "btn-close",
                callback: function () {
                    //$("#"+oname+"-power").destroy();
                    //return false;
                }
            },
            save: {
                label: "Save",
                className: "btn-primary",
                callback: function () {
                    var goon=true;
                    if ( $("#opasswd").val() != buddy.pass ) {
                        if ( $("#opasswd").siblings(".help-block").length == 0 ) {
                            $("#opasswd").closest(".form-group").append($("<p/>", {class: "help-block", html:"Password not correct"}));
                            $("#opasswd").closest(".form-group").addClass("has-warning");
                        }
                        goon=false;
                    } else {
                        $("#opasswd").closest(".form-group").removeClass("has-warning").addClass("has-success");
                        $("#opasswd").siblings(".help-block").remove();
                    }
                    if ( $("#npasswd").val() != $("#vpasswd").val()  ) {
                        if ( $("#npasswd").siblings(".help-block").length != 0 ) {
                            $("#npasswd").siblings(".help-block").remove();
                        }
                        $("#npasswd").closest(".form-group").append($("<p/>", {class: "help-block", html:"Passwords do not match"}));
                        $("#npasswd").closest(".form-group").addClass("has-warning");
                        goon=false;
                    } else { 
                        if ( $("#npasswd").val().length < 8) {
                            if ( $("#npasswd").siblings(".help-block").length != 0 ) {
                                $("#npasswd").siblings(".help-block").remove();
                            }
                            $("#npasswd").closest(".form-group").append($("<p/>", {class: "help-block", html:"Password must contain at least 8 characters."}));
                            $("#npasswd").closest(".form-group").addClass("has-warning");
                            goon=false;
                        } else {
                            $("#npasswd").closest(".form-group").removeClass("has-warning").addClass("has-success");
                            $("#npasswd").siblings(".help-block").remove();
                        }
                    }
                    
                    if (goon) {
                        var token = buddy.send_request("change password","control.users", buddy.subject,{"user":buddy.user,"password":buddy.pass,"new password":$("#npasswd").val()},["Password could not be changed",{"new password":$("#npasswd").val()}])
                        buddy.tokento[token]=setTimeout($.proxy(buddy.err_handle_property, buddy, token, "Password Change"), buddy.timeout);
                        
                    } else {
                        return false;
                    }
                }
            }
        }
    });
}
 
 
function manage_users () {
    
    var msg="<form class=\"form-mng-user\">"
    msg+="<div class=\"form-group\"><label for=\"ig-username\">User Name</label><div class = \"input-group\" id=\"ig-username\"><input class=\"form-control\" type=\"text\" name=\"User\" id=\"username\" />";
    msg+="<div id=\"bu-mng-user\" class = \"input-group-btn\"><button type = \"button\" class = \"btn btn-default dropdown-toggle\" data-toggle = \"dropdown\">";
    msg+="New User <span class = \"caret\"></span></button><ul class = \"dropdown-menu\">";
    msg+="<li><a href = \"#\">New User</a></li>";
    $.each(buddy.lousers, function(key, val) {
        msg+="<li><a href = \"#\">"+key+"</a></li>";
    })
    msg +="</ul></div>";
    msg +="</div></div>";
    msg +="<div class=\"form-group\"><label for=\"upasswd\">Password</label><input class=\"form-control\" type=\"password\" name=\"Password\" id=\"upasswd\" />";
    msg +="<label for=\"vpasswd\">Verify</label><input class=\"form-control\" type=\"password\" name=\"verPassword\" id=\"vpasswd\" /></div>";
    msg +="<div class=\"form-group\"><label for=\"location\">Location</label><select class=\"form-control\" type=\"select\" name=\"location\" id=\"bu-nu-location\" >";
    msg += zoneById[buddy.topzone].get_options();
    msg += "<option value=\"\" disabled>&mdash;&mdash;&mdash;&mdash;&mdash;</option>";
    msg += "<option value=\"admin\">Administrator</option>";
    msg += "</select>"
    msg +="</div>";
    msg +="</form>"
                        
    bootbox.dialog({
        title: "Manage Users",
        message:msg,
        buttons: {
            close: {
                label: "Cancel",
                className: "btn-close",
                callback: function () {
                    //$("#"+oname+"-power").destroy();
                    //return false;
                }
            },
            save: {
                label: "Save",
                className: "btn-primary",
                callback: function () {
                    var goon=true;

                    if ( $("#username").val() === undefined || $("#username").val().trim() == "" ) {
                        $("#username").closest(".form-group").append($("<p/>", {class: "help-block", html:"No Username"}));
                        $("#username").closest(".form-group").addClass("has-warning");
                        goon=false;
                    }
                    if (buddy.lousers[$("#username").val().trim()] === undefined ) {
                        if ( $("#upasswd").val() != $("#vpasswd").val()  ) {
                            if ( $("#upasswd").siblings(".help-block").length != 0 ) {
                                $("#upasswd").siblings(".help-block").remove();
                            }
                            $("#upasswd").closest(".form-group").append($("<p/>", {class: "help-block", html:"Passwords do not match"}));
                            $("#upasswd").closest(".form-group").addClass("has-warning");
                            goon=false;
                        } else { 
                            if ( $("#upasswd").val().length < 8 ) {
                                if ( $("#upasswd").siblings(".help-block").length != 0 ) {
                                    $("#upasswd").siblings(".help-block").remove();
                                }
                                $("#upasswd").closest(".form-group").append($("<p/>", {class: "help-block", html:"Password must contain at least 8 characters."}));
                                $("#upasswd").closest(".form-group").addClass("has-warning");
                                goon=false;
                            } else {
                                $("#upasswd").closest(".form-group").removeClass("has-warning").addClass("has-success");
                                $("#upasswd").siblings(".help-block").remove();
                            }
                        }
                    } else {
                            if ( $("#upasswd").val() && $("#upasswd").val().length < 8 ) {
                                if ( $("#upasswd").siblings(".help-block").length != 0 ) {
                                    $("#upasswd").siblings(".help-block").remove();
                                }
                                $("#upasswd").closest(".form-group").append($("<p/>", {class: "help-block", html:"Password must contain at least 8 characters."}));
                                $("#upasswd").closest(".form-group").addClass("has-warning");
                                goon=false;
                            } else {
                                $("#upasswd").closest(".form-group").removeClass("has-warning").addClass("has-success");
                                $("#upasswd").siblings(".help-block").remove();
                            }
                    }
                    
                    if (goon) {
                        var myval={"user":$("#username").val().trim(), "zone":$("#bu-nu-location").val().trim()}
                        if ( $("#upasswd").val()) {
                            myval["password"]=$("#upasswd").val();
                        }
                        var token = buddy.send_request("add user","control.users", buddy.subject,myval,["Usercould not be added",{"add user":[$("#username").val(),$("#bu-nu-location").val().trim()]}])
                        buddy.tokento[token]=setTimeout($.proxy(buddy.err_handle_property, buddy, token, "User Add/Edit"), buddy.timeout);
                        return true;
                    } else {
                        return false;
                    }
                }
            },
            delete: {
                label: "Delete",
                className: "btn-danger",
                callback: function () {
                    var goon=true;
                    
                    if ( $("#username").val() === undefined || $("#username").val().trim() == "" ) {
                        $("#username").closest(".form-group").append($("<p/>", {class: "help-block", html:"No Username"}));
                        $("#username").closest(".form-group").addClass("has-warning");
                        return false;
                    } else if ( buddy.lousers[$("#username").val().trim()] === undefined ) {
                        $("#username").closest(".form-group").append($("<p/>", {class: "help-block", html:"Unknown Username"}));
                        $("#username").closest(".form-group").addClass("has-warning");
                        return false;
                    } else if ( buddy.lousers[$("#username").val().trim()] == buddy.user) {
                        $("#username").closest(".form-group").append($("<p/>", {class: "help-block", html:"You cannot delete youself. Seek counseling."}));
                        $("#username").closest(".form-group").addClass("has-warning");
                    } else {
                        var token = buddy.send_request("delete user","control.users", buddy.subject,{"user":$("#username").val().trim()},["User "+$("#username").val()+" could not be deleted",{"delete user":$("#username").val()}])
                        buddy.tokento[token]=setTimeout($.proxy(buddy.err_handle_property, buddy, token, "Delete User"), buddy.timeout);
                    }
                }
            }
        }
    })
    $('#bu-mng-user ul.dropdown-menu li a').click(function (e) {
        var tuser = $(event.target)[0].innerHTML;
        if ( tuser == "New User" ) {
            $("#username").val("");
            $("#bu-nu-location").val(buddy.topzone);
        } else {
            $("#username").val(tuser);
            $("#bu-nu-location").val(buddy.lousers[tuser]);
        }
        return true;
    })
}

function devcompare(a,b) {
    if (a[0]< b[0]) {
        return -1;
    } else if (a[0] > b[0]) {
        return 1;
    }
    if (a[1]< b[1]) {
        return -1;
    } else if (a[1] > b[1]) {
        return 1;
    }
    if (a[2]< b[2]) {
        return -1;
    } else if (a[2] > b[2]) {
        return 1;
    }
    return 0
    
        
}

function bu_parse_xml(txt) {
    var thisdoc=$($.parseXML(txt));
    var myexpand={};
    var exidx=1
    //TODO  Add label, postfix and prefix transform for l10n
    
    $.each(thisdoc.find("[expand]"), function(key,eval) {
        var myex=$(eval).attr("expand")
        var mykey="bu-expansion-"+exidx;
        exidx+=1;
        $(eval).attr("expand",mykey)
        var options=$(eval).attr("exopt");
        if ($(eval).attr("label")!= undefined ) {
            var thisexpand="<controlgroup type=\"choice\" name=\""+$(eval).attr("name")+"\" label=\""+$(eval).attr("label")+"\" >";
        } else {
            var thisexpand="<controlgroup type=\"choice\" name=\""+$(eval).attr("name")+"\" label=\""+$(eval).attr("name")+"\" >";
        }
        $.each( myex.trim().split(","), function (k,exs) {
            var myexlist=exs.trim().split("::");
            var what = myexlist[0].toLowerCase();
            var dtype = myexlist[1];
            var dstype = myexlist[2];
            if (what == "device" ) {
                if (options != undefined && options.includes("withtype")) { var subtoo = true; } else { var subtoo=false; }
                var mylist=[];
                $.each( deviceById, function (idx, dev) {
                    if ( dtype==undefined || dev.type==dtype) {
                        if ( dstype==undefined || dev.type==dstype) {
                            mylist.push([dev.type,dev.subtype,dev.nickname,dev.name])
                        }
                    }
                });
                if (options != undefined && options.includes("any")) { thisexpand+="<item value=\"\" label=\"Any\" />"; }
                mylist.sort(devcompare);
                var ctype=undefined;
                var cstype=undefined;
                $.each( mylist, function (idx,val) {
                    if (val[0]!=ctype) {
                        ctype=val[0];
                        cstype=undefined;
                        if (subtoo) {
                            thisexpand+="<item value=\""+ctype+"\" />";
                        } else {
                            thisexpand+="<itemgroup value=\""+ctype+"\" />";
                        }
                    }
                    if (val[1]!=cstype) {
                        cstype=val[1];
                        if (subtoo) {
                            thisexpand+="<item value=\""+ctype+"."+cstype+"\" label=\"  "+cstype+"\" />";
                        } else {
                            thisexpand+="<itemgroup value=\"  "+cstype+"\" />";
                        }
                    }
                    thisexpand+="<item value=\""+ctype+"."+val[3]+"\" label=\"    "+val[2]+"\" />";
                })
            } else if (what=="config") {
                if (dtype != undefined && dstype != undefined && myexlist[3] != undefined && buddy.configs[dtype][dstype]!= undefined) {
                    //maybe we could check it is defined by a "listmaker" control?
                    //extracr a value based on dot separated keys
                    extractval= function (dict,key) { 
                        var x= dict; 
                        $.each( key.split("."), function (idx,k) {
                            x=x[k.trim()]
                        }); 
                        return x;
                    }
                    if (myexlist[4] != undefined && myexlist[5] != undefined) {
                        myfilter = function (x) { return extractval(x,myexlist[4]) == myexlist[5] };
                    } else {
                        myfilter = function (x) { return true };
                    }
                    var mylist=[];
                    $.each(buddy.configs[dtype][dstype][1],function (idx,val) {
                        $.each(val,function (jdx,wal) {
                            if (myfilter(wal)) {
                                mylist.push(extractval(wal,myexlist[3]));
                            }
                        })
                    })
                    mylist.sort()
                    $.each( mylist, function (idx,val) {
                        thisexpand+="<item value=\""+dtype+"."+dstype+"."+val+"\" label=\""+val+"\" />";
                    })
                } else {
                    console.log("Error: Cannot expand from \""+val+"\"");
                }
            } else if (what=="command") {
                var mylist=[];
                var seencmd=[];
                $.each( deviceById, function (idx, dev) {
                    if ( dtype==undefined || dev.type==dtype) {
                        if ( dstype==undefined || dev.type==dstype) {
                            mylist.push([dev.type,dev.subtype,dev.nickname,dev.name])
                        }
                    }
                })
                if (options == undefined || !options.includes("simplelist")) {
                    mylist.sort(devcompare);
                } 
                var ctype=undefined;
                var cstype=undefined;
                var cnlist=[];
                var clist={};
                $.each( mylist, function (idx,val) {
                    if (val[0]!=ctype) {
                        ctype=val[0];
                        cstype=val[1];
                        cnlist=[];
                        clist={}
                        cxml=$( jQuery.parseXML(buddy.functions[ctype][cstype])).find( "command" );
                        $.each(cxml.children(),function(idx,part) {
                            cnlist.push([$(part).attr("name"),$(part).attr("label")||$(part).attr("name")])
                            clist[$(part).attr("name")]=part.outerHTML;
                        });
                    }
                    if (options == undefined || !options.includes("simplelist")) {
                        thisexpand+="<item value=\""+ctype+"."+val[3]+"\" label=\""+val[2]+"\" >";
                        thisexpand+="<controlgroup type=\"choice\" name=\"command\">";
                    }
                    $.each(cnlist, function (idx,cval) {
                        if (options != undefined && options.includes("simplelist")) {
                            if (!seencmd.includes(cval[0]) ) {
                                seencmd.push(cval[0])
                                thisexpand+="<item value=\""+cval[0]+"\" label=\""+cval[1]+"\">"
                                thisexpand+=clist[cval[0]];
                                thisexpand+="</item>";
                            }
                        } else {
                            thisexpand+="<item value=\""+cval[0]+"\" label=\""+cval[1]+"\">"
                            thisexpand+=clist[cval[0]];
                            thisexpand+="</item>";
                        }
                    });
                    if (options == undefined || !options.includes("simplelist")) {
                        thisexpand+="</controlgroup></item>";
                    }
                });
            }
        })
        if ( options!= undefined && options.includes("freeform") ) {
            thisexpand+="<item value=\"freeform\" label=\"Specify\" >";
            thisexpand+="<control type=\"text\" name=\"freeform\" label=\" \" length=\"32\" />";
            thisexpand+="</item>";
        }
        thisexpand+="</controlgroup>";
        myexpand[mykey]=thisexpand;
    })

    $.each(myexpand, function (key,val) {
        thisdoc.find("[expand=\""+key+"\"]").replaceWith(val);
    });
    return thisdoc;
}

function module_config() {
    var msg = "<div id=\"bu-mod-config-choice\">";
    var ordered = {};
    Object.keys(buddy.configs).sort().forEach(function(key) {
        ordered[key] = buddy.configs[key];
    });
    buddy.configs=ordered;
    $.each(buddy.configs, function ( dtype, sub ) {
        ordered = {};
        Object.keys(buddy.configs[dtype]).sort().forEach(function(key) {
            ordered[key] = buddy.configs[dtype][key];
        });
        buddy.configs[dtype]=ordered;
    });
    $.each(buddy.configs, function ( dtype, sub ) {
        $.each(sub, function ( dstype, xml ) {
            msg+="<button type = \"button\" class = \"btn btn-default bu-mod-config-button\"  id=\"bu-mod-config-"+dtype+"."+dstype+"\">"+dtype+" "+dstype+"</button>";
        });
    });
    msg+="</div>";
    bootbox.dialog({
        title: "Select what to configure.",
        value: "conf",
        message:msg,
        buttons: {
        }
    });
    $(".bu-mod-config-button").on("click", module_config_bis);
}
    
function module_config_bis(e) {
    bootbox.hideAll();
    var elt = e.target.id.split("-").slice(-1)[0];
    var etype = elt.split(".")[0];
    var estype = elt.split(".")[1];
    buddy.cmd_panel = new buddyPanel("config",bu_parse_xml(buddy.configs[etype][estype][0]).find( "buddyui" ),false);
    buddy.cmd_panel.tgt = etype+"."+estype;
    var msg = buddy.cmd_panel.render("configuration");

    bootbox.dialog({
        title: "Configuration "+etype+" "+estype,
        value: "conf",
        message:msg,
        buttons: {
            close: {
                label: "Save",
                className: "btn-close",
                callback: function () {
                    var cval = buddy.cmd_panel.getValue();
                    var etype = buddy.cmd_panel.tgt.split(".")[0];
                    var ename = buddy.cmd_panel.tgt.split(".")[1];
                    var token=buddy.send_command("update config",ename,etype,cval,false,buddy.cmd_panel.tgt);
                    buddy.tokens.splice( $.inArray(token, buddy.tokens), 1 );
                    buddy.cmd_panel=null;
                }
            }
        }
    });
    buddy.cmd_panel.activate([250,0]);
    buddy.cmd_panel.setValue(buddy.configs[etype][estype][1])
}

function module_export_config() {
    var msg = "<div id=\"bu-mod-config-choice\">";
    msg+='<label for="bu-filename">Save to</label><input type="text" id="bu-filename" value="autobuddy.txt" placeholder="autobuddy.txt" /><br />'
    var ordered = {};
    Object.keys(buddy.configs).sort().forEach(function(key) {
        ordered[key] = buddy.configs[key];
    });
    buddy.configs=ordered;
    $.each(buddy.configs, function ( dtype, sub ) {
       msg+="<button type = \"button\" class = \"btn btn-default bu-mod-config-export-button\"  id=\"bu-mod-config-"+dtype+"\">Export "+dtype+"</button>";
    });
    msg+="</div>";
    bootbox.dialog({
        title: "Select what to export.",
        value: "conf",
        message:msg,
        buttons: {
        }
    });
    $(".bu-mod-config-export-button").on("click", module_export_config_bis);
}

function module_export_config_bis(e) {
    bootbox.hideAll();
    var elt = e.target.id.split("-").slice(-1)[0];
    var fn = $("#bu-filename").val();
    var exportval={}
    exportval[elt]={}
    $.each(buddy.configs[elt], function(key,val) {
        exportval[elt][key]=val[1];
    });
    
    blob = new Blob([JSON.stringify(exportval)], {type: "text/plain"}),
    url = window.URL.createObjectURL(blob);
    var anchor=$("<a/>").attr('href',url).attr("style","display: none").attr("download",fn);
    $("body").append(anchor);
    anchor[0].click();
    window.URL.revokeObjectURL(url);
    anchor.remove();
}



function module_import_config() {
    var msg = "<div id=\"bu-mod-config-choice\">";
    msg+='<label for="bu-fileinput">Read from</label><input type="file" id="bu-fileinput" /><br />';
    msg+="</div>";
    bootbox.dialog({
        title: "Select file to import.",
        value: "conf",
        message:msg,
        buttons: {
            close: {
                label: "Import",
                className: "btn-close",
                callback: function () {
                    module_import_config_bis();
                }
            }
        }
    });
    $(".bu-mod-config-export-button").on("click", module_import_config_bis);
}

function module_import_config_bis() {
    bootbox.hideAll();
    var fn = $("#bu-fileinput")[0].files[0];
    var reader = new FileReader();
    reader.readAsText(fn);
    reader.onload = function(e) {
        var notimp = "";
        var wasimp = "";
        var isep = "";
        var nsep = "";
        try {
            impval=JSON.parse(e.target.result);
            $.each(impval, function(tkey,tval) {
                if ( tkey in buddy.configs ) {
                    $.each(tval, function(stkey,stval) {
                        if ( stkey in buddy.configs[tkey] ) {
                            buddy.configs[tkey][stkey][1]=stval;
                            wasimp+=isep +tkey+"::"+stkey;
                            isep = ", ";
                            var token=buddy.send_command("update config",stkey,tkey,buddy.configs[tkey][stkey][1],false,tkey+"."+stkey);
                        } else {
                            notimp+=nsep +tkey+"::"+stkey;
                            nsep = ", ";
                        }
                    })
                } else {
                    notimp+=nsep +tkey;
                    nsep = ", ";
                }
            })
            if ( notimp == "" ) {
                bootbox.alert("Good! Everything was imported alright.");
            } else if ( wasimp == "" ) {
                bootbox.alert("Well... nothing was imported. Could be that the relevant buddies are not connected.");
            } else {
                
                bootbox.alert("Well... we imported this: "+wasimp+", but we failed to import this: "+notimp);
            }
        }
        catch (err) {
            bootbox.alert("Seems like the file you tried to import is just garbage: "+err.message);
        }
    };
}

function module_command() {
    var msg = "<div id=\"bu-mod-cmd-choice\">";
    var ordered = {};
    Object.keys(buddy.mcommands).sort().forEach(function(key) {
        ordered[key] = buddy.mcommands[key];
    });
    buddy.mcommands=ordered;
    $.each(buddy.mcommands, function ( stype, cmd ) {
        ordered = {};
        Object.keys(buddy.mcommands[stype]).sort().forEach(function(key) {
            ordered[key] = buddy.mcommands[stype][key];
        });
        buddy.mcommands[stype]=ordered;
    });
    $.each(buddy.mcommands, function ( stype, cmds ) {
        $.each(cmds, function ( cmd, cdef ) {
            msg+="<button type = \"button\" class = \"btn btn-default bu-mod-cmd-button\"  id=\"bu-mod-cmd-"+stype+"."+cmd+"\">"+cdef.label || (cmd+" "+stype)+"</button>";
        });
    });
    msg+="</div>";
    bootbox.dialog({
        title: "Select a command.",
        value: "cmd",
        message:msg,
        buttons: {
        }
    });
    $(".bu-mod-cmd-button").on("click", module_command_bis);
}   
function module_command_bis(e) {
    bootbox.hideAll();
    var elt = e.target.id.split("-").slice(-1)[0];
    var etype = elt.split(".")[0];
    var ecmd = elt.split(".")[1];
    buddy.send_command(ecmd,etype,buddy.mcommands[etype][ecmd]["module"],buddy.mcommands[etype][ecmd]["value"])
}

function explore_events() {
    var msg="<ul>";
    $.each(buddy.seenevents, function (idx,val) {
        msg+="<li>"+val+"</li>";
    })
    msg+="</ul>";
    bootbox.alert(msg);
}


// ES6 Alert. Using backquote for multi-lines
// Lifted from FontAwesome
// var notPresentIcon=`
//      <path class="bu-not-present" fill="#a94442" 
//            d="M1440 893q0-161-87-295l-754 753q137 89 297 89 111 0 211.5-43.5t173.5-116.5 116-174.5 43-212.5zm-999 299l755-754q-135-91-300-91-148
//               0-273 73t-198 199-73 274q0 162 89 299zm1223-299q0 157-61 300t-163.5 246-245 164-298.5 61-298.5-61-245-164-163.5-246-61-300 61-299.5 
//               163.5-245.5 245-164 298.5-61 298.5 61 245 164 163.5 245.5 61 299.5z"/>`;
var defaultIcon=`
    <svg  class="bu-device-icon" width="60" height="60" viewBox="0 0 1792 1792" xmlns="http://www.w3.org/2000/svg">
        <path  class="bu-fill"  stroke="black" stroke-width=1 d="M1152 896q0-106-75-181t-181-75-181 75-75 181 75 181 181 75 181-75 75-181zm512-109v222q0 
              12-8 23t-20 13l-185 28q-19 54-39 91 35 50 107 138 10 12 10 25t-9 23q-27 37-99 108t-94 71q-12 
              0-26-9l-138-108q-44 23-91 38-16 136-29 186-7 28-36 28h-222q-14 0-24.5-8.5t-11.5-21.5l-28-184q-49-16-90-37l-141 
              107q-10 9-25 9-14 0-25-11-126-114-165-168-7-10-7-23 0-12 8-23 15-21 51-66.5t54-70.5q-27-50-41-99l-183-27q-13-2-21-12.5t-8-23.5v-222q0-12 
              8-23t19-13l186-28q14-46 39-92-40-57-107-138-10-12-10-24 0-10 9-23 26-36 98.5-107.5t94.5-71.5q13 0 26 
              10l138 107q44-23 91-38 16-136 29-186 7-28 36-28h222q14 0 24.5 8.5t11.5 21.5l28 184q49 16 90 37l142-107q9-9 
              24-9 13 0 25 10 129 119 165 170 7 8 7 22 0 12-8 23-15 21-51 66.5t-54 70.5q26 50 41 98l183 28q13 2 21 12.5t8 23.5z"/>
              
        <path class="bu-not-present" fill="#a94442" 
           d="M1440 893q0-161-87-295l-754 753q137 89 297 89 111 0 211.5-43.5t173.5-116.5 116-174.5 43-212.5zm-999 299l755-754q-135-91-300-91-148
              0-273 73t-198 199-73 274q0 162 89 299zm1223-299q0 157-61 300t-163.5 246-245 164-298.5 61-298.5-61-245-164-163.5-246-61-300 61-299.5 
              163.5-245.5 245-164 298.5-61 298.5 61 245 164 163.5 245.5 61 299.5z"/>
    </svg>`;

/* A comment to clean highlighting */

var buddyIcons={};

var BuddyDevice = Class.extend({

    init: function(type,subtype,nickname,name) {
        this.type = type;
        this.subtype=subtype;
        this.name = name;
        this.nickname=nickname;
        this.parent = false;
        this.div = false;
        this.presence=false;
        this.status={};
        this.iconstatus={};
        this.info={};
        this.last_cmd;
        this.cmd_panel;
    },
    
    add_device_div: function() {
        var cdiv=$("<div>", {id: this.name, class: "zonedroppable bu-device "+"bu-"+this.type+" bu-"+this.subtype, 
                            "data-toggle":"tooltip","data-original-title":this.nickname});
        var devicon=false;
        if ( this.subtype in buddyIcons ) {
            devicon=buddyIcons[this.subtype];
        } else if ( this.type in buddyIcons ) {
            devicon=buddyIcons[this.type];
        } else {
            devicon= defaultIcon;
        }
        cdiv.append($(devicon));
        cdiv.draggable( {revert:  function(dropped) {
            if ($(this).hasClass('drag-revert')) {
                $(this).removeClass('drag-revert');
                return true;
            }
            if (! dropped) {
                return true;
            }
            return false;
        }, zIndex: 100 })
        this.div=true;
        cdiv.dblclick(this.device_dbl_click);
        cdiv.click(this.device_click);
        return cdiv
    },
    
    set_parent: function(parent) {
        if ( this.parent ) {
            var devicename=this.name;
            $.each(this.parent.devices,function(key,val) {
                if (val.name == devicename) {
                        deviceById[devicename].parent.devices.splice(key,1);;
                        return false;
                }
            });
            $device=$("#"+this.name).detach()
        } else if ( ! this.div ) {
            $device = this.add_device_div();
            this.div=true;
        } else {
            $device=$("#"+this.name).detach()
        }
        parent.devices.push(this);
        $("#"+parent.name).append($device);
        this.parent=parent;
    },
    
    match_status: function(cmd) {
        var self = this;
        $("#"+this.name).removeClass("run-animation")
        if ("animation" in this.iconstatus ) {
            $("#"+this.name+"_anim").remove();
            $("head").append("<style type=\"text/css\" id=\""+ this.name+"_anim\" >"+this.iconstatus.animation+"</style>")
        }
        $.each(this.iconstatus, function (eclass,val) {
            if ( eclass != "animation" ) {
                $.each(val, function (attr,aval) {
                    try {
                        document.getElementById( self.name ).getElementsByClassName(eclass)[0].setAttribute(attr,aval);
                    }
                    catch (err)  {};
                })
            }
        });
        if ("animation" in this.iconstatus ) {
            $("#"+this.name).addClass("run-animation")
        }
    },
    
    device_dbl_click: function() {
        if (buddy.editmode) {
            /*change name panel*/
            var oname = this.id;
            var otype = deviceById[this.id].type;
            var zz = deviceById[this.id].nickname
            bootbox.prompt({
                title: "Change Device Name",
                value: zz,
                callback: function(result) {
                    if (result === null) {
                    } else {
                        var token = buddy.send_command("nickname", oname, otype,result);
                    }
                }
            });
        } else {
            //Command and control
        }
        return false;
    },
    
    device_click: function() {
        if (! buddy.editmode && deviceById[this.id].presence) {
            /*Create a modal with an on/off switch*/
            var oname = this.id;
            var otype = deviceById[this.id].type;
            var stype = deviceById[this.id].subtype;
            var zz = deviceById[this.id].nickname;
            var self = deviceById[this.id];

            if(buddy.functions[otype] && buddy.functions[otype][stype] ) {
                self.cmd_panel = new buddyPanel(oname,bu_parse_xml(buddy.functions[otype][stype]).find( "buddyui" ),true);
                var msg = self.cmd_panel.render("command");

                bootbox.dialog({
                    title: "Control "+otype+" "+zz,
                    value: zz,
                    message:msg,
                    buttons: {
                        close: {
                            label: "Close",
                            className: "btn-close",
                            callback: function () {
                                //$("#"+oname+"-power").destroy();
                                //return false;
                            //    deviceById[oname].match_status();
                            }
                        }
                    }
                });
                self.cmd_panel.activate([250,0]);
                self.cmd_panel.setValue(deviceById[oname].status);
                self.cmd_panel.setCallback(deviceById[oname].exec_rtcommand)
            }
        }
        return false;
    },
    
    exec_rtcommand: function(event) {
        var allelt = event.target.id.split("__");
        if (! allelt || allelt.length <2) {
            var anelt = $(event.target).parent().closest('div.bu-widget')[0];
            if ( anelt ) {
                allelt = anelt.id.split("__");
            } else {
                return false;
            }
        }
        var target = allelt[0];
        var cmd = allelt[1];
        buddy.send_command(cmd,target,deviceById[target].type,deviceById[target].cmd_panel.getValue()[cmd],undefined,undefined,{"realtime mode":true});
        return false;
    },

        
    refresh: function (width) {
        /* 
        * Resizing the icon on change, max is 60x60, minimum number of devs 
        */
        if (width>60) {
            width=60;
        }
        if ( document.getElementById( this.name ) ) {
            document.getElementById( this.name ).getElementsByClassName("bu-device-icon")[0].setAttribute("width",width);
            document.getElementById( this.name ).getElementsByClassName("bu-device-icon")[0].setAttribute("height",width);
        }
    }
})

var BuddyZone = Class.extend({
    init: function (nickname,name) {
        if (name === null) {
            this.name=Math.random().toString(36).substr(2);
        } else {
                this.name=name;
        }
        this.nickname=nickname;
        this.parent = false;
        this.children= [];
        this.devices=[];
        this.div = false;
    },
         
    set_parent: function (up) {
        if (this.parent != up ) {
            var sdiv = false;
            if (this.parent != false ) {
                sdiv = this.parent.remove_zone_div(this);
            }
            this.parent = up;
            up.append_zone_div(this,sdiv);
        }
            
    },
     
    get_parent: function ()  {
         return this.parent;
    },
     
    get_path: function () {
         if (this.parent == false ) {
             return "."+this.name
         }
         
         return this.parent.get_path() + "." + this.name;
    },
          
    get_depth: function () {
         if (this.parent == false ) {
             return 0;
         }
         
         return this.parent.get_depth() + 1;
    },
 
    get_options: function() {
        var mydepth=this.get_depth();
        res="<option value=\""+this.name+"\">";
        if (mydepth ) {
            res+="&nbsp;&nbsp;".repeat(mydepth)+" ";
        }
        res+=this.nickname+"</option>"
        $.each(this.children,function(key,val) {
            res += val.get_options();
        })
        return res;
    },
    
    append_zone_div: function  (child,adiv) {
        this.children.push(child);
        var cdiv;
        if ( child.div == true ) {
            cdiv = adiv;
        } else {
            cdiv=this.add_zone_div(child);
            child.div=true;
        }
        $("#"+this.name).append(cdiv);
        this.refresh();
    },
    
    add_zone_div: function(child) {
        var cdiv=$("<div>", {id: child.name, class: "bu-zone zonedroppable"});
        var ldiv =$("<p>", {class: "bu-zonelabel label"}).html("Zone "+child.nickname);
        cdiv.append(ldiv);
        cdiv.draggable( {revert:  function(dropped) {
            if ($(this).hasClass('drag-revert')) {
                $(this).removeClass('drag-revert');
                return true;
            }
            if (! dropped) {
                return true;
            }
            return false;
        }, zIndex: 100 })
        cdiv.droppable({
            accept: ".zonedroppable",
            greedy:true,
            activeClass: "ui-state-default",
            hoverClass: "ui-state-hover",
            drop: function( event, ui ) {
                buddy.drop_zone(event,ui,this);
            }
        });
        cdiv.dblclick(this.zone_dbl_click);
        return cdiv
    },
     
    remove_zone_div: function (child) {
        $child=$("#"+child.name);
        var sdiv = $child.detach();
        this.children=this.children.filter( function (i) {
            return i != child
        })
        this.refresh()
        return sdiv
   },
     
    destroy_zone: function () {
        $.each(this.children,function(key,val) {
            val.destroy_zone()
        })
        delete zoneById[this.name];
        if ( buddy.debug ) { console.log("Did delete "+this.name); }
   },
        
    refresh: function () {
        /* 
            * Resizing the div on change
            */
        var pwidth = $('#'+this.name).innerWidth();
        var delta = 1;
        var pheight = $('#'+this.name).innerHeight()-5 ;
       
        var pendingdev=[];
        $.each(this.devices,function(key,val) {
            pendingdev.push($("#"+val.name).detach());
        })
        
        var ar = pwidth / pheight ;
        var nbchildren = $('#'+this.name).children("div").length;
        var nbrow = 1;
        var nbcol = 1;
        while ( nbrow * nbcol < nbchildren + delta) {
            if ( nbcol > nbrow ) {
                nbrow = nbrow + 1;
            } else {
                nbcol = nbcol +1 ;
            }
        }
        var subzw = Math.floor(pwidth / nbcol);
        var subzh = Math.floor(pheight / nbrow);
        var depth =  this.get_depth();

        if ( this.name == buddy.currenttop ) {
            if ( this.name == buddy.topzone ) {
                $('#'+this.name).addClass("bu-layer-colour-0-0");
            } else {
                var idx=0;
                for (var i=0; i<this.parent.children.length; i++) {
                    if (this.parent.children[i].name==this.name) {
                        idx=i;
                        break;
                    }
                }
                $('#'+this.name).addClass("bu-layer-colour-"+depth+"-"+idx);
            }
        }
        $('#'+this.name).children("div").each( function (i,elt) {
            $("#"+elt.id).css("width",subzw);
            $("#"+elt.id).css("height",subzh);
            $("#"+elt.id).css("float","left");
            $("#"+elt.id).addClass("bu-layer-colour-"+(depth+1)+"-"+i);
            }
        )
        for (var i=0; i < this.children.length; i++) {
            this.children[i].refresh();
        };
        
        for (var i=0; i < pendingdev.length; i++) {
            $("#"+this.name).append(pendingdev[i]);
        };
        
        var cdiff= (nbcol*nbrow) - this.children.length;
        var awidth = (pwidth/nbcol)*cdiff;
        var aheight = pheight/nbrow;
        var nbdevs = this.devices.length;
        var px=Math.ceil(Math.sqrt(nbdevs*awidth/aheight));
        var sx,sy;
        if (Math.floor(px*aheight/awidth)*px <  nbdevs)  {//not fit
            sx=aheight/Math.ceil(px*aheight/awidth);
        } else {
            sx= awidth/px;
        }
        var py=Math.ceil(Math.sqrt(nbdevs*aheight/awidth));
        if ( Math.floor(py*awidth/aheight)*py < nbdevs) { //not fit
            sy=awidth/Math.ceil(awidth*py/aheight);
        } else {
            sy=aheight/py;
        }
        var iwidth = Math.max(sx,sy);
        $.each(this.devices,function(key,val) {
            val.refresh(iwidth);
        })
    },
     
    anchor: function (elt) {
         /*
          * Used to anchor the top zone to the domain/
          */
        
        var cdiv=$("<div>", {id: this.name, class: "bu-topzone zonedroppable"});
        $("#"+elt).append(cdiv);
        this.div=true;
        $("#"+this.name).css("width",$("#"+elt).innerWidth());
        $("#"+this.name).css("height",$("#"+elt).innerHeight());
        cdiv.droppable({
                accept: ".zonedroppable",
                greedy:true,
                activeClass: "ui-state-default",
                hoverClass: "ui-state-hover",
                drop: function( event, ui ) {
                    buddy.drop_zone(event,ui,this);
                }
                });
        $("#"+this.name).append($("<p>", {class: "bu-zonelabel label"}).html("Zone "+this.nickname));
        this.refresh()
    },
     
    reanchor: function(elt) {
        if (buddy.currenttop != this.name) { 
            $(".bu-topzone").remove();
            this.anchor(elt);
            this.rebuild_children()
            if (this.parent) {
                $("#"+this.name+" > .bu-zonelabel").append($("<span>", {class:" bu-zoneup "}).html("&nbsp;&nbsp;<i class=\"fa fa-arrow-up fa-3x\"></i> "));
                $(".bu-zoneup").click(this.parent.name,function (ev) {
                    zoneById[ev.data].reanchor(elt);
                    $('[data-toggle="tooltip"]').tooltip({placement : 'top'});
                })
            }
            buddy.currenttop=this.name;
            $(".bu-zonelabel").click(zoneById[buddy.currenttop].zone_click);
            this.refresh();
        }
     },
     
    rebuild_children: function () {
        for (var i=0; i < this.children.length; i++) {
            $("#"+this.name).append(this.add_zone_div(this.children[i]));
            this.children[i].rebuild_children();
        }
    
        for (var i=0; i < this.devices.length; i++) {
            $("#"+this.name).append(this.devices[i].add_device_div());
            this.devices[i].match_status();
        }
     },
     
    build_children: function (children) {
        var self=this;
        $.each(children,function(key,val) {
            if ( val["name"] ) {
                var nz = buddy.add_zone(val["nickname"],self,val["name"]);
            } else {
                var nz = buddy.add_zone(val["name"],self);
            }
            $.each(val["devices"],function(type,devices) {
                $.each(devices,function(idx,subdevice) {
                    var adevice=new BuddyDevice(type,subdevice["subtype"],subdevice["nickname"],subdevice["name"]);
                    adevice.set_parent(nz)
                    deviceById[adevice.name]=adevice
                })
            })
            nz.build_children(val["sub_zone"]);
        })
    },
  
    revert_devices: function() {
        $.each(this.children,function(key,val) {
           val.revert_devices();
        })
        var lonames=[];
        $.each(this.devices,function(key,val) {
            lonames.push(val.name);
        })
        $.each(lonames, function(kek,name) {
            deviceById[name].set_parent(zoneById["zone-BuddyRoot"])
        })
    },
    
    zone_dbl_click: function() {
        if (buddy.editmode) {
            /*change name panel*/
            var oname = this.id;
            var zz = zoneById[this.id].nickname
            bootbox.prompt({
                title: "Change Zone Name",
                value: zz,
                callback: function(result) {
                    if (result === null) {
                    } else {
                        var token = buddy.send_request("zone nickname", "control.zone", buddy.subject,{"name":oname,"nickname": result},[oname]);
                        buddy.tokento[token]=setTimeout($.proxy(buddy.err_handle_zone_naming, buddy, token, zoneById), buddy.timeout);
                    }
                }
            });
            return false
        } else {
            zoneById[this.id].reanchor("bu-topzonec");
            $('[data-toggle="tooltip"]').tooltip({placement : 'top'});
            return false
        }
    },
    
    zone_click: function() {
        if (! buddy.editmode) {
            /*Create amodakl with an on/off switch*/
            var oname = $(this).closest("div").attr("id");
            var otype = "zone"
            var zz = zoneById[oname].nickname;
            var msg="<input type=\"checkbox\" id=\""+oname+"-power\" data-indeterminate=\"true\">";
            bootbox.dialog({
                title: "Control "+otype+" "+zz+"<span style=\"float: right; margin-right: 20px;\"><input type=\"checkbox\" id=\""+oname+"-propagate\" >&nbsp;Also sub-zone</span>",
                value: zz,
                message:msg,
                buttons: {
                    close: {
                        label: "Close",
                        className: "btn-close",
                        callback: function () {
                        }
                    }
                }
            });
            $("#"+oname+"-power").bootstrapSwitch();
            $("#"+oname+"-power").on("switchChange.bootstrapSwitch",function (ev,state) {
                buddy.send_command("power",oname,otype,(state && "on") || "off",$("#"+oname+"-propagate").is(':checked'))
            })
        } 
        return false
    }

 })
 
var BuddyMsg = Class.extend({
     init: function (subject,type) {
         this.subject = subject;
         this.content_type = type;
         this.content = {} ;
         this.content.token=Math.random().toString(36).substr(2) + Math.random().toString(36).substr(2);
     },
     
     json: function () {
         return JSON.stringify(this);
     }
})
 
var BuddyApp = Class.extend({
    init: function(subject,ws) {
        this.tokens = [];
        this.tokeninfo={};
        this.tokento={};
        this.functions={};
        this.configs={};
        this.socket = ws;
        this.subject = subject;
        this.isopen = false;
        this.autologin=false;
        this.editmode=false;
        this.topzone = false;
        this.currenttop = false;
        this.isadmin = false;
        this.zonecnt = 0;
        this.timeout = 5000;
        this.user = false;
        this.lousers={};
        this.pass = false;
        this.debug= false ;
        this.cmd_panel=null;
        this.seenevents=[];
        
        this.socket.binaryType = "arraybuffer";
        this.socket.onopen = function() {
            if ( buddy.debug ) { console.log("Connected!"); }
            isopen = true;
            var uname = get_cookie("buddyuser");
            var upass = get_cookie("buddypass");
            if (uname) {
                if ( buddy.debug ) { console.log("Auto login On"); }
                this.autologin = true ;
                buddy.send_login(uname,upass);
            }
            buddy.build_login();
        }
        this.socket.onmessage = function(e) {
            if (typeof e.data == "string") {
                if ( buddy.debug ) { console.log("Text message received: " + e.data); }
            } else {
                var arr = new Uint8Array(e.data);
                var hex = '';
                for (var i = 0; i < arr.length; i++) {
                    hex += ('00' + arr[i].toString(16)).substr(-2);
                }
                if ( buddy.debug ) { console.log("Binary message received: " + hex);}
            }
            var msg = JSON.parse(e.data);
            if (msg.content_type == 'response' ) {
                if ( buddy.tokento[msg.content.token] ) {
                    clearTimeout(buddy.tokento[msg.content.token]);
                    delete buddy.tokento[msg.content.token] ;
                }
                if (jQuery.inArray( msg.content.token, buddy.tokens) >= 0) {
                    buddy.tokens.splice( $.inArray(msg.content.token, buddy.tokens), 1 );
                    if ( msg.content.response ==  'login' ) {
                        buddy.handle_login(msg);
                    } else if ( msg.content.response ==  'system state' ) {
                        buddy.handle_state(msg)
                    } else if ( msg.content.response ==  'zone creation' ) {
                        buddy.handle_zone_creation(msg)
                    } else if ( msg.content.response ==  'zone location' ) {
                        buddy.handle_zone_location(msg)
                    } else if ( msg.content.response ==  'zone deletion' ) {
                        buddy.handle_zone_deletion(msg)
                    } else if ( msg.content.response ==  'zone nickname' ) {
                        buddy.handle_zone_naming(msg)
                    } else if ( msg.content.response ==  'device location' ) {
                        buddy.handle_device_location(msg)
                    } else if ( msg.content.response ==  'define device' ) {
                        buddy.handle_device_define(msg)
                    } else if ( msg.content.response ==  'save property' ) {
                        buddy.handle_property(msg)
                    }
                }
            } else if (msg.content_type == 'event' ) {
                if ( msg.content.event ==  'status' ) {
                    buddy.hevent_device_status(msg);
                } else if ( msg.content.event ==  'info' ) {
                    buddy.hevent_device_info(msg);
                } else if ( msg.content.event ==  'presence' ) {
                    buddy.hevent_device_presence(msg);
                } else if ( msg.content.event ==  'new device' ) {
                    buddy.hevent_device_new(msg);
                } else if ( msg.content.event ==  'nickname' ) {
                    buddy.hevent_device_nickname(msg);
                } else if ( msg.content.event ==  'device location' ) {
                    buddy.hevent_device_location(msg);
                } else if ( msg.content.event ==  'zone creation' ) {
                    buddy.hevent_zone_creation(msg);
                } else if ( msg.content.event ==  'zone location' ) {
                    buddy.hevent_zone_location(msg);
                } else if ( msg.content.event ==  'zone deletion' ) {
                    buddy.hevent_zone_deletion(msg);
                } else if ( msg.content.event ==  'zone nickname' ) {
                    buddy.hevent_zone_naming(msg);
                } else if ( msg.content.event ==  'gui info' ) {
                    buddy.hevent_bridge_info(msg);
                } else if ( msg.content.event ==  'config updated' ) {
                    buddy.hevent_command_updt(msg);
                } else if ( msg.content.event ==  'gui alert' ) {
                    buddy.hevent_gui_alert(msg);
                } else if ( msg.content.event ==  'deletion' ) {
                    buddy.hevent_device_deletion(msg);
                } else if ( msg.content.event ==  'error report' ) {
                    console.log(msg.content.value);
                }
                if ( "icon status" in msg.content ) {
                    if ("target" in msg.content) {
                        var device=msg.content.target.split(".")[1];
                        deviceById[device].iconstatus=msg.content["icon status"];
                        deviceById[device].match_status(msg.content.subject);
                        if ( msg.content.event in deviceById[device].status && "value" in msg.content ) {
                            //Should we check if it is a command for that?
                            deviceById[device].status[msg.content.subject] = msg.content.value;
                        }
                    }
                }
                //Let's record the event structure
                if ( msg.content.event !=  'gui info' ) {
                    var newevents = get_dict_keys(msg.content.value);
                    if ( $.isArray( newevents) ) {
                        $.each(newevents, function (idx,val) {
                            buddy.seenevents.push(msg.content.target.split("-")[0]+"  "+msg.content.event+"  value::"+val)
                        })
                    } else if ( newevents=="") {
                        buddy.seenevents.push(msg.content.target.split("-")[0]+"  "+msg.content.event+"  value")
                    } else {
                        buddy.seenevents.push(msg.content.target.split("-")[0]+"  "+msg.content.event+"  value::"+newevents)
                    }
                    buddy.seenevents = Array.from(new Set(buddy.seenevents));
                    buddy.seenevents.sort();
                }

            }
        }
        this.socket.onclose = function(e) {
            if ( buddy.debug ) { console.log("Connection closed."); }
            this.socket = null;
            this.isopen = false;
            bootbox.dialog({
                title: "Connection Lost",
                value: "OMG",
                message:`<p>We are terribly sorry. The server has gone the way of the dodo. 
                            You might want to try to reload a bit later. As of now this whole contraption is pretty much useless.</p>`,
                buttons: {
                    close: {
                        label: "Close",
                        className: "btn-close",
                        callback: function () {
                        }
                    }
                }
            });
        }
    },
    
    handle_login: function (msg) {
        if ( msg.content.status == 'failed' ) {
            $(".form-signin :input").attr("disabled", false);
            if ( ! this.autologin ) {
                $(".form-signin").addClass("has-error");
                $(".form-signin .help-block").html("Could not login")
            } else {
                this.autologin = false;
            }
        } else {
            if ($('.form-signin :checkbox').is(':checked')) {
                set_cookie('buddyuser',$("#inputName").val());
                set_cookie('buddypass',$("#inputPassword").val())
            }
            if ( $("#inputName").val() == "" ) {
                this.user = get_cookie("buddyuser");
                this.pass = get_cookie("buddypass");
            } else {
                this.user = $("#inputName").val();
                this.pass = $("#inputPassword").val();
            }
            $('.form-signin').remove();
            if ( msg.content.zone == "admin" ) {
                this.isadmin=true;
                if ( msg.content.value) {
                    this.lousers=msg.content.value["list of users"]
                }
            } else {
                this.topzone=msg.content.zone
            }
            buddy.build_panel();
            $("#bu-navbar-menu > li").removeClass("disabled");
        }
    },
    
    not_handle_login: function (token) {
    },
    
    handle_state: function (msg) {
        if ( msg.content.status == 'failed' ) {
            /*Display something silly*/
        } else {
            var tzone=msg.content["value"]["sub_zone"][0] /* There should only be one...should we check? */
            var topzone=buddy.add_zone(tzone["nickname"],"",tzone["name"]);
            if (this.isadmin) {
                this.topzone=tzone["name"];
            }

            if ( "about" in msg.content["value"] ) {
                $.each(msg.content["value"]["about"],function(key,text) {
                    abouttext[key]=text
                })
            }
            if ( "display" in msg.content["value"] ) {
                $.each(msg.content["value"]["display"],function(key,text) {
                    buddyIcons[key]=text
                })
            }
            $.each(tzone["devices"],function(type,devices) {
                $.each(devices,function(idx,subdevice) {
                    var adevice=new BuddyDevice(type,subdevice["subtype"],subdevice["nickname"],subdevice["name"]);
                    adevice.set_parent(topzone)
                    deviceById[adevice.name]=adevice
                })
            })
            this.currenttop=tzone["name"];
            topzone.build_children(tzone["sub_zone"])
            /* Find the top zone number */
            var ccount=this.zonecnt;
            $.each(zoneById,function(key,val) {
                var cnt = parseInt(val.nickname.split(" ").pop());
                if ( cnt != NaN && cnt >= ccount ) {
                    ccount= cnt+1;
                }
            })
            this.zonecnt = ccount;
            this.functions= msg.content["value"]["functions"];
            this.configs= msg.content["value"]["configs"];
            this.mcommands= msg.content["value"]["module commands"];
            $('[data-toggle="tooltip"]').tooltip({placement : 'top'});
            $(window).resize(function() {
                $("#"+buddy.currenttop).css("width",$("#bu-topzonec").innerWidth());
                $("#"+buddy.currenttop).css("height",$("#bu-topzonec").innerHeight());
                zoneById[buddy.currenttop].refresh();
            });
            /*Build the menu */
            if (this.isadmin) {
                var nelt = $('<li/>');
                nelt.append($('<button/>',{ class: "btn btn-default navbar-btn", onclick:"buddy.edit_mode(!buddy.editmode);", html:"Edit Mode", id:"edit-mode-button"}));
                nelt.append($('<label/>', {for: "edit-mode-button", class: "sr-only", html:"Toggle Edit mode"}));
                $('#bu-navbar').append(nelt);
                nelt = $('<li/>');
                var pelt = $('<p/>', {class: "nav navbar-text zonedroppable bu-admin-menu", html:"New Zone", id:"bu-add_zone"});
                pelt.draggable( {helper: "clone", revert: "invalid", zIndex: 100 })
                pelt.draggable("disable");
                pelt.hide();
                nelt.append(pelt);
                $('#bu-navbar').append(nelt);
                nelt = $('<li/>');
                pelt = $('<span/>', {class: "nav navbar-text bu-admin-menu", html:"<i class=\"fa fa-trash-o fa-lg\"></i> Delete", id:"bu-delZone"});
                /*pelt.append($("<i/>",{class: "fa fa-trash-o fa-lg"}))*/
                pelt.droppable({
                    accept: ".bu-zone, .bu-device",
                    greedy:true,
                    activeClass: "ui-state-default",
                    hoverClass: "ui-state-hover",
                    tolerance:"pointer",
                    drop: function( event, ui ) {
                        buddy.drop_delete_zone_dev(event,ui,this);
                    }
                });
                pelt.hide();
                nelt.append(pelt);
                $('#bu-navbar').append(nelt);
                nelt = $('<li/>');
                pelt=$('<button/>',{ class: "btn btn-default navbar-btn bu-admin-menu", onclick:"manage_users();", html:"Manage Users", id:"manage_users"});
                nelt.append($('<label/>', {for: "manage_users", class: "sr-only", html:"Manage Users"}));
                pelt.hide();
                nelt.append(pelt);
                $('#bu-navbar').append(nelt);
            }
            topzone.refresh();
            this.edit_mode(this.editmode);
            $.each(deviceById,function(idx,device) {
                buddy.send_command("status",device.name,device.type,"")
            })
            $(".bu-zonelabel").click(zoneById[buddy.currenttop].zone_click);
                
        }
    },
    
    not_handle_state: function (token) {
    },
     
    send_login: function (user,passwd) {
        var msg = new BuddyMsg("control.login","request");
        msg.content.request = "login";
        msg.content.target = this.subject;
        msg.content.user = user;
        msg.content.password = passwd;
        this.tokens.push(msg.content.token);
        this.socket.send(msg.json());
    },
 
    send_command: function (command,target, sendto, value,propagate,targetonly,options) {
        var msg = new BuddyMsg(sendto+"."+target,"command");
        msg.content.command = command;
        msg.content.value = value;
        if (propagate) {
            msg.content.propagate=propagate;
        }
        if (targetonly) {
            msg.content.target = targetonly;
        } else {
            msg.content.target = sendto;
        }
        if ( options ) {
            $.each( options, function (key,val) {
                msg.content[key]=val;
            });
        }
        //console.log("Sending"+msg.json());
        this.socket.send(msg.json());
    },
    
    send_event: function (event,target, value) {
        var msg = new BuddyMsg(target,"event");
        msg.content.target = target;
        msg.content.event = event;
        if (value) {
            msg.content.value = value;
        }
        this.socket.send(msg.json());
    },
    
    send_request: function (request,target, device, value, tovalue) {
        var msg = new BuddyMsg(target,"request");
        msg.content.target = device;
        msg.content.request = request;
        if (value) {
            msg.content.value = value;
        }
        this.tokens.push(msg.content.token);
        if (tovalue ) {
            this.tokeninfo[msg.content.token]=tovalue;
        }
        this.socket.send(msg.json());
        return msg.content.token
    },
    
    build_login:  function () {
        $('#top-container').html($('<form/>', {action: '', class: "form-signin"}));
        var aelt =$('<h2/>',{ class: "form-signin-heading" });
        aelt.html("Please log-in");
        $('.form-signin').append(aelt);
        $('.form-signin').append($('<h3/>',{ class: "form-signin-heading, help-block"}));
        $('.form-signin').append($('<label/>', {for: "inputName", class: "sr-only"}));
        $('.form-signin :last-child').html("Your username")
        $('.form-signin').append($("<input/>", { type: "text", id: "inputName", class: "form-control", placeholder: "Your username"}));
        $('.form-signin :last-child').prop("required", true);
        $('.form-signin :last-child').prop("autofocus", true);
        $('.form-signin').append($('<label/>', {for: "inputPassword", class: "sr-only"}));
        $('.form-signin :last-child').html("Password");
        $('.form-signin').append($("<input/>", { type: "password", id: "inputPassword", class: "form-control", placeholder: "Your username"}));
        $('.form-signin :last-child').prop("required", true);
        aelt = $("<div/>", { class: "checkbox"} );
        var albl = $("<label />", { html:"Remember Me?"});
        albl.prepend($("<input/>", { type: "checkbox", value: "remember-me"}));
        aelt.append(albl);
        $('.form-signin').append(aelt);
        $('.form-signin').append($("<button/>",{ class: "btn btn-lg btn-primary btn-block", type: "submit"}));
        $('.form-signin :button').html("Log in");
        
        $("form").submit(function( event ) {
                event.preventDefault();
                buddy.send_login($("#inputName").val(),$("#inputPassword").val());  
                $(".form-signin :input").attr("disabled", true);
            });
        
    },
    
    build_panel: function() {
        $('#top-container').append($('<div/>', {class: "no-gutter col-xs-12 col-md-12", id: "bu-topzonec"}));
        //var ctrldiv=$('<div/>',{ class: "col-md-4", id: "bu-tools" });
        //ctrldiv.append($('<div/>', {class: "bu-nldevs", id: "bu-nldevs"}));
        //ctrldiv.append($('<div/>', {class: "bu-controls ", id: "bu-controls"}));
        //$('#top-container').append(ctrldiv);
        var zinfo=""
        if (this.topzone) {
            zinfo={"zone":this.topzone}
        }
            
        var token = this.send_request("system state","control", "gui",zinfo );
    },
         
    add_zone: function (nickname,parent,name) {
        if ( buddy.debug ) { console.log("Adding "+nickname); }
        var nz= new BuddyZone(nickname,name);
        if ( parent == "" ) {
            nz.anchor("bu-topzonec");
            $( window ).resize(function() {
                nz.refresh()
            })
        } else {
            nz.set_parent(parent) ;
        }
        this.edit_mode(this.editmode)
        zoneById[nz.name]=nz;
        return nz;
    },
    
    drop_zone: function (event,ui,dropin) {
        $(ui.draggable).css({left:'auto',top:"auto"}); 
        if (ui.draggable[0].id == "bu-add_zone") {
            var pname = zoneById[dropin.id].name;
            var nzname="zone-"+Math.random().toString(36).substr(2);
            var token = this.send_request("zone creation", "control.zone", this.subject, {"parent":pname,"name":nzname, "nickname":nznametmpl+this.zonecnt},[dropin.id]);
            this.zonecnt++;
            this.tokento[token]=setTimeout($.proxy(buddy.err_handle_zone_creation, buddy, token, zoneById), this.timeout);
        } else {
            if ($("#"+ui.draggable[0].id).hasClass("bu-device")) {
                // A device
                if ( deviceById[ui.draggable[0].id].parent ) {
                    var opname = deviceById[ui.draggable[0].id].parent.name;
                } else {
                    var opname = false;
                }
                var name = deviceById[ui.draggable[0].id].name;
                var pname = zoneById[dropin.id].name;
                if ( opname != pname ) {
                    var token = this.send_request("device location", "control.zone", this.subject,{"name":name,"parent": pname},[ui.draggable[0].id,dropin.id]);
                    this.tokento[token]=setTimeout($.proxy(buddy.err_handle_device_location, buddy, token, deviceById), this.timeout);
                }
                
            } else {
                //A zone
                var opname = zoneById[ui.draggable[0].id].parent.name;
                var name = zoneById[ui.draggable[0].id].name;
                var pname = zoneById[dropin.id].name;
                if ( opname != pname ) {
                    var token = this.send_request("zone location", "control.zone", this.subject,{"name":name,"parent": pname},[ui.draggable[0].id,dropin.id]);
                    this.tokento[token]=setTimeout($.proxy(buddy.err_handle_zone_location, buddy, token, zoneById), this.timeout);
                }
            }
        } 
    },
         
    handle_zone_naming: function(msg) {
        if ( msg.content.status == 'failed' ) {
            /*Display something silly*/
            if ( this.tokeninfo[msg.content.token]) {
                var nzname = "Zone "+zoneById[this.tokeninfo[msg.content.token][0]].nickname;
                delete this.tokeninfo[msg.content.token];
                
            } else {
                var nzname = "Zone";
            }
            bootbox.alert(nzname+" could not be renamed.");
        } else {
            if ( this.tokeninfo[msg.content.token]) {
                delete this.tokeninfo[msg.content.token];
            }
        }
    },
         
    hevent_zone_naming: function(msg) {
        var type=msg.content.target.split(".")[0];
        if (type == "zone") {
            var zid=msg.content.target.split(".")[1];
            if ( zid in zoneById) {
                var nickname=msg.content.value["nickname"]
                zoneById[zid].nickname=nickname;
                $("#"+zid+" .bu-zonelabel").first().html("Zone "+nickname);
            }
        }
    },
    
    err_handle_zone_naming: function (token) {
        if ( this.tokeninfo[token]) {
            var nzname = "Zone "+zoneById[this.tokeninfo[token][0]].nickname;
            delete this.tokeninfo[token];
        } else {
            var nzname = "Zone";
        }
        bootbox.alert(nzname+" could not be renamed.");
    },
    
    handle_zone_location: function(msg) {
        if ( msg.content.status == 'failed' ) {
            /*Display something silly*/
            if ( this.tokeninfo[msg.content.token]) {
                var nzname = "Zone "+zoneById[this.tokeninfo[msg.content.token][0]].nickname;
                delete this.tokeninfo[msg.content.token];
                
            } else {
                var nzname = "New Zone";
            }
            bootbox.alert(nzname+" could not be relocated.");
        } else {
            if ( this.tokeninfo[msg.content.token]) {
                delete this.tokeninfo[msg.content.token];
            }
        }
    },
    
    hevent_zone_location: function(msg) {
        var type=msg.content.target.split(".")[0];
        if (type == "zone") {
            var zid=msg.content.target.split(".")[1];
            
            if ( zid in zoneById) {
                var pid = msg.content.value["parent"];
                zoneById[zid].set_parent(zoneById[pid]);
                zoneById[pid].refresh();
            }
        }
    },
    
    err_handle_zone_location: function (token) {
        if ( this.tokeninfo[token]) {
            var nzname = "Zone "+this.tokeninfo[token][0];
            delete this.tokeninfo[token];
        } else {
            var nzname = "Zone";
        }
        bootbox.alert(nzname+" could not be moved.");
    },
    
    handle_zone_creation: function(msg) {
        if ( msg.content.status == 'failed' ) {
            /*Display something silly*/
            if ( this.tokeninfo[msg.content.token]) {
                var nzname = "Zone "+this.tokeninfo[msg.content.token][0];
                delete this.tokeninfo[msg.content.token];
                
            } else {
                var nzname = "New Zone";
            }
            bootbox.alert(nzname+" could not be created.");
        } else {
            if ( this.tokeninfo[msg.content.token]) {
                delete this.tokeninfo[msg.content.token];
            }
        }
    },
    
    hevent_zone_creation: function(msg) {
        var type=msg.content.target.split(".")[0];
        if (type == "zone") {
            var zid=msg.content.target.split(".")[1];
            var pid = msg.content.value["parent"];
            var nickname = msg.content.value["nickname"];
            if ( zoneById[zid] === undefined ) {
                var nz=buddy.add_zone(nickname,zoneById[pid],zid);
            }
        }
    },
       
    err_handle_zone_creation: function (token) {
        if ( this.tokeninfo[token]) {
            var nzname = "New Zone in "+this.tokeninfo[token][0];
            delete this.tokeninfo[token];
        } else {
            var nzname = "New Zone";
        }
        bootbox.alert(nzname+" could not be created.");
    },
    
    drop_delete_zone_dev: function (event,ui,dropin) {
        $(ui.draggable).addClass('drag-revert');
        if ( $(ui.draggable[0]).hasClass("bu-zone" )) {
            $(ui.draggable).hide();
            this.delete_zone(zoneById[ui.draggable[0].id].name);
        } else if ( $(ui.draggable[0]).hasClass("bu-device" )) {
            $(ui.draggable).hide();
            this.delete_device(deviceById[ui.draggable[0].id]);
           
        }
    },
    
    delete_zone: function(name) {
        if ( buddy.debug ) { console.log("Deleting "+name); }
        var token = this.send_request("zone deletion", "control.zone", this.subject, {"name":name},name);
        this.tokento[token]=setTimeout($.proxy(buddy.err_handle_zone_deletion, buddy, token, zoneById), this.timeout);
    },
     
    handle_zone_deletion: function(msg) {
        var thisapp = this;
        if ( msg.content.status == 'failed' ) {
             if ( buddy.debug ) { console.log("Delete Failed"); }
            if ( this.tokeninfo[msg.content.token]) {
                $.each(zoneById,function(key,val) {
                    if (val.name == thisapp.tokeninfo[msg.content.token]) {
                        $("#"+val.name).show();
                        return false;
                    }
                });
                delete this.tokeninfo[msg.content.token];
            }
            /*Display something silly*/
            bootbox.alert("The controller refused to delete");
        } else {
            if ( this.tokeninfo[msg.content.token]) {
                delete this.tokeninfo[msg.content.token];
            }
        }
    },
    
    hevent_zone_deletion: function(msg) {
        var type=msg.content.target.split(".")[0];
        if (type == "zone") {
            var zonename=msg.content.target.split(".")[1];
            if ( zonename in zoneById) {
                zoneById[zonename].revert_devices();
                $.each(zoneById,function(key,val) {
                    if (val.name == zonename) {
                            $("#"+val.name).remove();
                            return false;
                    }
                });
                
                $.each(zoneById[zonename].parent.children,function(key,val) {
                    if (val.name == zonename) {
                            zoneById[zonename].parent.children.splice(key,1);;
                            return false;
                    }
                });
                zoneById[zonename].destroy_zone();
                zoneById[this.currenttop].refresh()
            }
        }
    },
       
    err_handle_zone_deletion: function (token, zoneById) {
        if ( this.tokeninfo[token]) {
            var thisapp=this;
            $.each(zoneById,function(key,val) {
                if (val.name == thisapp.tokeninfo[token]) {
                    $("#"+val.name).show();
                    return false;
                }
            });
            delete this.tokeninfo[token];
        };
    },
    
    edit_mode: function(mode) {
         if (mode) {
             $('#bu-topzone').droppable("enable");
             $('.bu-zone').droppable("enable");
             $('.bu-zone').draggable("enable");
             $('.bu-device').draggable("enable");
             $("#edit-mode-button").addClass("btn-primary");
             $('#bu-add_zone').draggable("enable");
             $('#bu-navbar .bu-admin-menu').show()
//              $('#bu-add_zone').show();
//              $('#bu-delZone').show();
         } else {
             $('#bu-topzone').droppable("disable");
             $('.bu-zone').droppable("disable");
             $('.bu-zone').draggable("disable");
             $('.bu-device').draggable("disable");
             $("#edit-mode-button").removeClass("btn-primary");
             $('#bu-add_zone').draggable("disable");
             $('#bu-navbar .bu-admin-menu').hide()
//              $('#bu-add_zone').hide();
//              $('#bu-delZone').hide();
         };
         this.editmode=mode;
     },
    
    delete_device: function(device) {
        if ( buddy.debug ) { console.log("Deleting "+device.name); }
        var token = device.name
        this.send_command("deletion",device.name,device.type,device.name);
        this.tokento[token]=setTimeout($.proxy(buddy.err_handle_device_deletion, buddy, token, deviceById), this.timeout);
    },
    
    hevent_device_deletion: function(msg) {
        var type=msg.content.target.split(".")[0];
        var devid=msg.content.target.split(".")[1];
        if ( devid in deviceById) {
            $("#"+devid).remove();
            delete this.tokento[devid];
            delete deviceById[devid];
            return false;
        }
    },
       
    err_handle_device_deletion: function (token, deviceById) {
        if ( this.tokento[token]) {
            var thisapp=this;
            $("#"+token).show();
            delete this.tokento[token];
            return false;
        };
    },
       

    hevent_device_status: function(msg) {
        var type=msg.content.target.split(".")[0];
        var device=msg.content.target.split(".")[1];
        if (deviceById[device]) {
            if (deviceById[device].type==type) {
                deviceById[device].presence=true;
                $.each(msg.content.value,function(key,value) {
                    deviceById[device].status[key]=value;
                })
                if ( "icon status" in msg.content ) {
                    deviceById[device].iconstatus=msg.content["icon status"];
                }
            }
            deviceById[device].match_status();
        }
    },
    
    hevent_device_presence: function(msg) {
        var type=msg.content.target.split(".")[0];
        var device=msg.content.target.split(".")[1];
        if ( deviceById[device]) {
             if ( deviceById[device].type == type ) {
                if ( "icon status" in msg.content ) {
                    deviceById[device].iconstatus=msg.content["icon status"];
                }
                deviceById[device].presence= ( msg.content.value == "online" )
                if ( msg.content.value == "online" ) {
                    buddy.send_command("status",deviceById[device].name,deviceById[device].type,"");
                } else {
                    deviceById[device].match_status();
                }
            }
        }
    },
    
    hevent_device_new: function(msg) {
        var type=msg.content.target.split(".")[0];
        var device=msg.content.target.split(".")[1];
        if (! deviceById[device]) {
             //Check some consistency
            if ( ( type != msg.content.value["type"] ) || (device != msg.content.value["name"] )) {
                 if ( buddy.debug ) { console.log("Warning: message not consistent "+type," != "+msg.content.value["type"]+" or "+device+" != "+msg.content.value["name"] )}
            } else {
                
                if (zoneById["zone-BuddyRoot"]) {
                    var adevice=new BuddyDevice(type,msg.content.value["subtype"],msg.content.value["nickname"],device);
                    adevice.set_parent(zoneById["zone-BuddyRoot"])
                    deviceById[adevice.name]=adevice
                    $('[data-toggle="tooltip"]').tooltip({placement : 'top'});
                }
            }
        }
    },
    
    handle_device_location: function(msg) {
        if ( msg.content.status == 'failed' ) {
            /*Display something silly*/
            if ( this.tokeninfo[msg.content.token]) {
                var nzname = "Device "+deviceById[this.tokeninfo[msg.content.token][0]].nickname;
                delete this.tokeninfo[msg.content.token];
                
            } else {
                var nzname = "Device";
            }
            bootbox.alert(nzname+" could not be relocated.");
        } else {
            if ( this.tokeninfo[msg.content.token]) {
                delete this.tokeninfo[msg.content.token];
            }
        }
    },
    
    hevent_device_location: function(msg) {
        var type=msg.content.target.split(".")[0];
        var device=msg.content.target.split(".")[1];
        var parent=msg.content.value["parent"];
        if ( deviceById[device] ) {
            deviceById[device].set_parent(zoneById[parent]);
            zoneById[parent].refresh();
        } else {
            var token = this.send_request("define device", "control.zone", this.subject,{"name":name});
        }
    },
    
    err_handle_device_location: function(token) {
        if ( this.tokeninfo[token]) {
            var nzname = "Device "+this.tokeninfo[token][0];
            delete this.tokeninfo[token];
        } else {
            var nzname = "Device";
        }
        bootbox.alert(nzname+" could not be moved.");
    },
   
    handle_device_define: function(msg) {
        if ( msg.content.status == 'done' ) {
            var type=msg.content.target.split(".")[0];
            var device=msg.content.target.split(".")[1];
            if (! deviceById[device]) {
                var adevice=new BuddyDevice(msg.content.value["type"],msg.content.value["subtype"],msg.content.value["nickname"],msg.content.value["name"]);
                adevice.set_parent(zoneById[msg.content.value["parent"]])
                deviceById[adevice.name]=adevice
                $('[data-toggle="tooltip"]').tooltip({placement : 'top'});
            }
        }
    },
    
    hevent_device_nickname: function(msg) {
        var type=msg.content.target.split(".")[0];
        var device=msg.content.target.split(".")[1];
        if ( deviceById[device]) {
             if ( deviceById[device].type == type ) {
                deviceById[device].nickname= msg.content.value;
                $("#"+deviceById[device].name).attr('data-original-title', msg.content.value).tooltip('fixTitle')
            }
        }
    },
    
    hevent_device_info: function(msg) {
        var type=msg.content.target.split(".")[0];
        var device=msg.content.target.split(".")[1];
        if ( deviceById[device]) {
             if ( deviceById[device].type == type ) {
                deviceById[device].info = msg.content.value;
            }
        }
    },
    
    handle_property: function(msg) {
        if ( msg.content.status == 'failed' ) {
            /*Display something silly*/
            if ( this.tokeninfo[msg.content.token]) {
                var infoname = this.tokeninfo[msg.content.token][0];
                delete this.tokeninfo[msg.content.token];
            } else {
                var infoname = "Information  could not be saved.";
            }
            bootbox.alert(infoname);
        } else {
            if ( this.tokeninfo[msg.content.token]) {
                if (this.tokeninfo[msg.content.token][1]) {
                    if (this.tokeninfo[msg.content.token][1]["new password"]) {
                        this.pass=this.tokeninfo[msg.content.token][1]["new password"]
                    } else if (this.tokeninfo[msg.content.token][1]["add user"]) {
                        this.lousers[this.tokeninfo[msg.content.token][1]["add user"][0]]=this.tokeninfo[msg.content.token][1]["add user"][1]
                    } else if (this.tokeninfo[msg.content.token][1]["delete user"]) {
                        delete(this.lousers[this.tokeninfo[msg.content.token][1]["delete user"]])
                    }
                }
                delete this.tokeninfo[msg.content.token];
            }
        }
    },
    
    err_handle_property: function(token) {
        if ( this.tokeninfo[token] && this.tokeninfo[token][0]) {
            var infoname = this.tokeninfo[token][0];
            delete this.tokeninfo[token];
        } else {
            var infoname = "Information could not be saved.";
        }
        bootbox.alert(infoname);
    },

    hevent_bridge_info: function(msg) {
        if (msg.content["about"]) {
            $.each(msg.content["about"], function(key,val) {
                    abouttext[key]=val;
            })
        }
    },

    hevent_command_updt: function(msg) {
        if (msg.content["target"]) {
            var etype = msg.content["target"].split(".")[0];
            var estype = msg.content["target"].split(".")[1];
            if ( etype in buddy.configs && estype in buddy.configs[etype] ) {
                $.each(msg.content["value"], function(key,val) {
                        buddy.configs[etype][estype][1][key]=val;
                })
            }
        }
    },
    
    hevent_gui_alert: function(msg) {
        $("<span>").text(msg["content"]["value"]).appendTo('#bu-navbar-info').delay(7000).queue(function() {$(this).remove();});
    }
    
})