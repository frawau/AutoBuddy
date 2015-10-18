/*!
 * AutoBuddy JavaScript Library v0.1
 * http://jquery.com/

 * Copyright 2015 François Wautier
 * Released under the MIT license
 *
 * Date: 2015-08-16
*/
/* 
* I do Python
*/
var False = false;
var True = true;

var colourSchemes = [["hsl(180,100%,90%)", "hsl(260,30%,40%)"],["hsl(270,100%,90%)", "hsl(350,30%,40%)"],["hsl(0,100%,90%)", "hsl(80,30%,40%)"],["hsl(90,100%,90%)", "hsl(170,30%,40%)"]]
var nbScheme = colourSchemes.length;
var maxchild = 12;
var childstep = 4;
var zoneById={};
var deviceById={};
var nznametmpl = "New Zone "; /* New Zone name template */

/*
* Some utility functions
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
  

function generateBGClass() {
    var cssstr = "<style>\n.bu-layer-colour-0-0 { border-bottom-color: #C63D0F; border-right-color: #C63D0F;}\n";
    
    
    for (var i=0; i < colourSchemes.length; i++) {
        var color = d3.scale.linear(d3.interpolateHsl)
                .domain([0, maxchild])
                .range(colourSchemes[i]);
        for (var k=0; k < childstep; k++) {
            for (var j=k; j < maxchild; j+=childstep) {
                cssstr+=".bu-layer-colour-"+(i+1)+"-"+j+" {border-bottom-color: "+color(j)+"; border-right-color: "+color(j)+";}\n";
            }
        }
    };
    $('html > head').append(cssstr);
}

function whiteToRGB(K) {
    // Taken from
    // http://www.TannerHelland.com/4435/convert-temperature-rgb-algorithm-code/
    // http://www.zombieprototypes.com/?p=210
    var red=0;
    var green=0;
    var blue=0;
    if ( K <= 6600 ) {
        red=255;
    } else {
        var a = 351.97690566805693;
        var b = 0.114206453784165;
        var c = -40.25366309332127;
        var x = ( K / 100 ) - 55 ;
        red=Math.round(a+b*x+c*Math.log(x));
        if ( red < 0) {
            red = 0;
        } else if ( red > 255) {
            red=255;
        }
    }
    
    if ( K <= 6600 ) {
        var a = -155.25485562709179;
        var b = -0.44596950469579133;
        var c = 104.49216199393888;
        var x = ( K / 100 ) - 2;
    } else {
        var a = 325.4494125711974;
        var b = 0.07943456536662342;
        var c = -28.0852963507957;
        var x = ( K / 100 ) - 50;
    }
    
    green=Math.round(a+b*x+c*Math.log(x));
    if ( green < 0) {
        green = 0;
    } else if ( green > 255) {
        green=255;
    }
    
    if ( K >= 6600 ) {
        blue=255;
    } else {
        var a = -254.76935184120902;
        var b = 0.8274096064007395;
        var c = 115.67994401066147;
        var x = ( K / 100 ) - 10;
        blue=Math.round(a+b*x+c*Math.log(x));
        if ( blue < 0) {
            blue = 0;
        } else if ( blue > 255) {
            blue=255;
        }
    }
    return new RGBColour(red,green,blue);
}


function setCookie(key, value) {
    var expires = new Date();
    expires.setTime(expires.getTime() + (7 * 24 * 60 * 60 * 1000));
    document.cookie = key + '=' + value + ';expires=' + expires.toUTCString();
}

function getCookie(key) {
    var keyValue = document.cookie.match('(^|;) ?' + key + '=([^;]*)(;|$)');
    return keyValue ? keyValue[2] : null;
}
 
function logout() {
    document.cookie = "buddyuser=; expires=Thu, 01 Jan 1970 00:00:01 GMT;";
    document.cookie = "buddypass=; expires=Thu, 01 Jan 1970 00:00:01 GMT;";
    location.reload()
}
 
function showAbout () {
    var msg="<ul class=\"nav nav-tabs\">"
    var tabmsg = "<div id=\"about-tab-content\" class=\"tab-content\">";
    var active = " active";
    var haslic = false;
    var keylist = [];
    $.each(abouttext, function(key,val) {
        if (key=="License") {
            haslic=true;
        } else {
            keylist.push(key);
        }
    })
    keylist.sort();
    if ( haslic ) {
        keylist.push("License");
    }
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

function changePassword () {
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
                        var token = buddy.sendRequest("change password","control.users", buddy.subject,{"user":buddy.user,"password":buddy.pass,"new password":$("#npasswd").val()},["Password could not be changed",{"new password":$("#npasswd").val()}])
                        buddy.tokento[token]=setTimeout($.proxy(buddy.nhProperty, buddy, token, "Password Change"), buddy.timeout);
                        
                    } else {
                        return false;
                    }
                }
            }
        }
    });
}
 
 
function manageUsers () {
    
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
                        var token = buddy.sendRequest("add user","control.users", buddy.subject,myval,["Usercould not be added",{"add user":[$("#username").val(),$("#bu-nu-location").val().trim()]}])
                        buddy.tokento[token]=setTimeout($.proxy(buddy.nhProperty, buddy, token, "User Add/Edit"), buddy.timeout);
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
                        var token = buddy.sendRequest("delete user","control.users", buddy.subject,{"user":$("#username").val().trim()},["User "+$("#username").val()+" could not be deleted",{"delete user":$("#username").val()}])
                        buddy.tokento[token]=setTimeout($.proxy(buddy.nhProperty, buddy, token, "Delete User"), buddy.timeout);
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

function webConfig() {
    bootbox.alert("We are very sorry. This has not been implemented yet. But when we do, it will be great.... We promis!")
}
// ES6 Alert. Using backquote for multi-lines
// Lifted from FontAwesome
var notPresentIcon=`
     <path class="bu-not-present" fill="#a94442" 
           d="M1440 893q0-161-87-295l-754 753q137 89 297 89 111 0 211.5-43.5t173.5-116.5 116-174.5 43-212.5zm-999 299l755-754q-135-91-300-91-148
              0-273 73t-198 199-73 274q0 162 89 299zm1223-299q0 157-61 300t-163.5 246-245 164-298.5 61-298.5-61-245-164-163.5-246-61-300 61-299.5 
              163.5-245.5 245-164 298.5-61 298.5 61 245 164 163.5 245.5 61 299.5z"/>`;
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
        this.last_cmd;
    },
    
    addDeviceDiv: function() {
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
        cdiv.dblclick(this.deviceDblClick);
        cdiv.click(this.deviceClick);
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
            $device = this.addDeviceDiv();
            this.div=true;
        } else {
            $device=$("#"+this.name).detach()
        }
        parent.devices.push(this);
        $("#"+parent.name).append($device);
        this.parent=parent;
    },
    
    matchStatus: function(cmd) {
        if (this.presence) {
            $("#"+this.name+" .bu-not-present").css("opacity",0);
            if ( this.status["power"] ) {
                if ( this.status["power"] == "off" ) {
                    document.getElementById( this.name ).getElementsByClassName("bu-fill")[0].setAttribute("fill","transparent");
                } else {
                    if (cmd === undefined && this.last_cmd) {
                        cmd=this.last_cmd;
                    }
                    if ( cmd ) {
                        if ( cmd == "colour" ) {
                            var col = new HSVColour(this.status["colour"]["hue"],this.status["colour"]["saturation"],this.status["colour"]["value"])
                            document.getElementById( this.name ).getElementsByClassName("bu-fill")[0].setAttribute("fill",col.getCSSHexadecimalRGB());
                        }
                        if ( cmd == "color" ) {
                            var col = new HSVColour(this.status["colour"]["hue"],this.status["colour"]["saturation"],this.status["colour"]["value"])
                            document.getElementById( this.name ).getElementsByClassName("bu-fill")[0].setAttribute("fill",col.getCSSHexadecimalRGB());
                        }
                        if ( cmd == "white" ) {
                            var col = whiteToRGB(this.status["white"]["temperature"]);
                            document.getElementById( this.name ).getElementsByClassName("bu-fill")[0].setAttribute("fill",col.getCSSHexadecimalRGB());
                        }
                    } else {
                        if ( this.status["colour"] &&  this.status["colour"]["saturation"]>1) {
                            var col = new HSVColour(this.status["colour"]["hue"],this.status["colour"]["saturation"],this.status["colour"]["value"])
                            document.getElementById( this.name ).getElementsByClassName("bu-fill")[0].setAttribute("fill",col.getCSSHexadecimalRGB());
                        }
                        else if ( this.status["color"]  &&  this.status["colour"]["saturation"]>1) {
                            var col = new HSVColour(this.status["color"]["hue"],this.status["color"]["saturation"],this.status["color"]["value"])
                            document.getElementById( this.name ).getElementsByClassName("bu-fill")[0].setAttribute("fill",col.getCSSHexadecimalRGB());
                        } else if ( this.status["white"]) {
                            var col = whiteToRGB(this.status["white"]["temperature"]);
                            document.getElementById( this.name ).getElementsByClassName("bu-fill")[0].setAttribute("fill",col.getCSSHexadecimalRGB());
                        } else {
                            document.getElementById( this.name ).getElementsByClassName("bu-fill")[0].setAttribute("fill","white");
                        }
                    }
                }
            }
        } else {
            document.getElementById( this.name ).getElementsByClassName("bu-fill")[0].setAttribute("fill","transparent");
            $("#"+this.name+" .bu-not-present").css("opacity",1);
        }
    },
    
    deviceDblClick: function() {
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
                        var token = buddy.sendCommand("nickname", oname, otype,result);
                    }
                }
            });
            return false
        } else {
            //Command and control
        }
    },
    
    deviceClick: function() {
        if (! buddy.editmode && deviceById[this.id].presence) {
            /*Create amodakl with an on/off switch*/
            var oname = this.id;
            var otype = deviceById[this.id].type;
            var stype = deviceById[this.id].subtype;
            var zz = deviceById[this.id].nickname;
            var locontrols = {"slider":[],"switch":[],"knob":[],"modal":[], "spinner":[], "colourpicker":[]};
            var msg="";
            var tabmsg = "<div id=\"my-tab-content\" class=\"tab-content\">";
            var active = " active";
            if(buddy.functions[otype] && buddy.functions[otype][stype] ) {
                var $cmd=$( jQuery.parseXML(buddy.functions[otype][stype])).find( "buddyui" );
                msg+="<ul class=\"nav nav-tabs\">"
                $.each($cmd.children(), function (idx, apart) {
                    var part = $(apart);
                    var lbl = part.attr("label");
                    var cmdname = $(part).attr("name");
                    msg+="<li role=\"presentation\" class=\"bu-commandtab"+active+"\"><a href=\"#"+oname+"-"+cmdname+"\"  data-toggle=\"tab\">"+lbl+"</a></li>";
                    tabmsg+="<div class=\"tab-pane bu-commandpanel"+ active+"\" id=\""+oname+"-"+cmdname+"\">";
                    if ( part.is("controlgroup") ) {
                        var domodal=False
                        if (part.attr("modal") && part.attr("modal") == '1') {
                            domodal=True;
                        } 
                        if (part.attr("widget")) {
                           var resu = deviceById[oname].create_widget(part.attr("widget") ,cmdname,"bu-modal-colourpick")
                           locontrols[resu[0]].push([resu[1],domodal]);
                           tabmsg+=resu[2];
                        } else {
                            if (part.children().filter("control").length < 3 ) {
                                var hidx = 0;
                            } else if (part.children().filter("control").length > 5 ) {
                                var hidx=part.children().length -1;
                            } else {
                                var hidx = -1;
                            }
                            $.each(part.children().filter("control"), function (jdx, actrl) {
                                var resu = deviceById[oname].create_control($(actrl),cmdname,(jdx == hidx))
                                locontrols[resu[0]].push([resu[1],domodal]);
                                tabmsg+=resu[2];
                                if (jdx == hidx) {
                                    hidx+=1;
                                }
                            });
                        }
                        if ( domodal ) {
                            //Check for options
                            $.each(part.children().filter("option"), function (jdx, actrl) {
                                var resu = deviceById[oname].create_control($(actrl),cmdname,true,"buopt-"+oname+"-"+cmdname)
                                tabmsg+="<br />"+resu[2];
                            })
                            tabmsg+="<br /><button type=\"button\" class=\"btn btn-default\" ";
                            tabmsg+="id=\"modal__"+oname+"__"+cmdname;
                            tabmsg+="\">Apply</button>";
                            locontrols["modal"].push("modal__"+oname+"__"+cmdname);
                        }
                    } else if ( part.is("control") ) {
                        var resu = deviceById[oname].create_control(part,cmdname,true)
                        locontrols[resu[0]].push([resu[1],false]);
                        tabmsg+=resu[2];
                    }
                    tabmsg+="</div>";
                    active = "";
                })
                msg+="</ul>"+tabmsg+"</div>"
            }
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
                            deviceById[oname].matchStatus();
                        }
                    }
                }
            });
            $.each(locontrols["switch"], function (idx, vals) {
                var aswitch = vals[0];
                var modal = vals[1];
                $("#"+aswitch).bootstrapSwitch();
                if (! modal) {
                    $("#"+aswitch).on("switchChange.bootstrapSwitch",deviceById[oname].exec_swcmd)
                }
            })
            $.each(locontrols["slider"], function (idx, vals) {
                var slider = vals[0];
                var modal = vals[1];
                $("#"+slider).bootstrapSlider({precision: 2});
                if (! modal) {
                    $("#"+slider).on("slide",deviceById[oname].exec_slcmd)
                    $("#"+slider).on("change",deviceById[oname].exec_slcmd)
                }
            })
            $.each(locontrols["colourpicker"], function (idx, vals) {
                var cmd = vals[0];
                var modal = vals[1]
                var rcmd = cmd.split("__");
                var rdev = rcmd[0];
                rcmd = rcmd[1];
                var h = deviceById[rdev].status[rcmd]["hue"];
                var s = deviceById[rdev].status[rcmd]["saturation"];
                var v = deviceById[rdev].status[rcmd]["value"];
                var cw = colourwheel($("#"+cmd)[0],250)
                cw.set_colour([h,s,v])
                if (! modal) {
                    cw.onchange(deviceById[oname].exec_colcmd)
                }
            })
            
            $.each(locontrols["modal"], function (idx, modal) {
                $("#"+modal).on("click",deviceById[oname].exec_modalcmd)
            })
        }
        return false;
    },
    
    exec_slcmd: function(event) {
        //"this" is a DOM elt
        var allelt = this.id.split("__");
        var target = allelt[0];
        var cmd = allelt[1];
        var param = allelt[2];
        var newval={}
        $.each(deviceById[target].status[cmd], function(key, value) {
//             newval[key]=$("#"+target+"__"+cmd+"__"+key).bootstrapSlider('getValue')
            newval[key]=$("#"+target+"__"+cmd+"__"+key).val()
        })
        buddy.sendCommand(cmd,target,deviceById[target].type,newval)
        deviceById[target].last_cmd=cmd
    },
    
    exec_swcmd: function(event,state) {
        //"this" is a DOM elt
        var allelt = this.id.split("__");
        var target = allelt[0];
        var cmd = allelt[1];
        var param = allelt[2];
        var newval={};
        buddy.sendCommand(cmd,target,deviceById[target].type,(state && $(this).attr("bu-on-cmdvalue")) || $(this).attr("bu-off-cmdvalue"))
    },
        
    exec_colcmd: function(colour) {
        //"this" is a DOM elt
        var allelt = $(".bu-modal-colourpick").attr("id").split("__");
        var target = allelt[0];
        var cmd = allelt[1];
        var param = allelt[2];
        var newval={}
        newval["hue"]=colour[0];
        newval["saturation"]=colour[1];
        newval["value"]=colour[2];
        buddy.sendCommand(cmd,target,deviceById[target].type,newval)
        deviceById[target].last_cmd=cmd
    },
    
    exec_modalcmd: function(event,state) {
        //"this" is a DOM elt
        var allelt = this.id.split("__");
        var target = allelt[1];
        var cmd = allelt[2];
        var newval={}
        $.each(deviceById[target].status[cmd], function(key, value) {
//             newval[key]=$("#"+target+"__"+cmd+"__"+key).bootstrapSlider('getValue')
            newval[key]=$("#"+target+"__"+cmd+"__"+key).val();
        })
        var opts={}
        $(".buopt-"+target+"-"+cmd).each( function () {
            var myelt = this.id.split("__");
            var opt = myelt[2];
            opts[opt]=$(this).val();
        })
        buddy.sendCommand(cmd,target,deviceById[target].type,newval,false,false,opts)
        this.last_cmd=cmd
    },
    
    
    create_widget: function ( widget,cmdname,classes ) {
        if ( widget == "colourpicker" ) {
            var tabmsg = "<div id=\""+this.name+"__"+cmdname+"\"";
            if (classes) {
                tabmsg += " class=\""+classes+"\" "
            }
            tabmsg += "/>";
            var col = new HSVColour(this.status[cmdname]["hue"],this.status[cmdname]["saturation"],this.status[cmdname]["value"])
            return ["colourpicker",this.name+"__"+cmdname,tabmsg]
        }
    },
            
            
    create_control: function ( ctrl,cmdname,horiz,classes ) {
        if ( ctrl.attr("type") == "slider" ) {
            var tabmsg = "<label class=\"bu-label\"  for=\""+this.name+"__"+cmdname+"__"+ctrl.attr("name")+"\">"+ctrl.attr("label")+"</label>"
            tabmsg += "<input id=\""+this.name+"__"+cmdname+"__"+ctrl.attr("name")+ "\" type=\"text\" ";
            tabmsg += "data-slider-min=\""+ctrl.find("start").text()+"\" data-slider-max=\""+ctrl.find("end").text();
            tabmsg += "\" data-slider-step=\""+ctrl.find("increment").text();
            tabmsg += "\" data-slider-value=\""+deviceById[this.name].status[cmdname][ctrl.attr("name")]+"\" ";
            if (classes) {
                tabmsg += " class=\""+classes+"\" "
            }
            if (horiz) {
                tabmsg+="/><br />"
            } else {
                tabmsg+="data-slider-orientation=\"vertical\" data-slider-reverse=\"1\"";
                tabmsg+="/>";
              
            }
            return ["slider",this.name+"__"+cmdname+"__"+ctrl.attr("name"),tabmsg];

        } else if ( ctrl.attr("type") == "knob" ) {
        } else if ( ctrl.attr("type") == "switch" ) {
            var tabmsg = "<label class=\"bu-label\" for=\""+this.name+"__"+cmdname+"__"+ctrl.attr("name")+"\">"+(ctrl.attr("label") || ctrl.attr("name"))+"</label>"
            tabmsg +="<input type=\"checkbox\" id=\""+this.name+"__"+cmdname+"\" ";
            var self=this;
            $.each(ctrl.children().filter("value"), function (idx, aval) {
                var  val=$(aval);
                if (idx == 0) {
                    tabmsg+=" data-on-label=\""+val.attr("label")+"\" "
                    tabmsg+=" bu-on-cmdvalue=\""+val.text()+"\" "
                    if ( deviceById[self.name].status[cmdname] == val.text() ) {
                        tabmsg +="checked "
                    }
                } else {
                    tabmsg+=" data-off-label=\""+val.attr("label")+"\" "
                    tabmsg+=" bu-off-cmdvalue=\""+val.text()+"\" "
                }
            }) 
            if (classes) {
                tabmsg += " class=\""+classes+"\" "
            }
            tabmsg+=" />";
            return ["switch",this.name+"__"+cmdname,tabmsg];
        } else if ( ctrl.attr("type") == "spinner" ) {
            var tabmsg = "<label class=\"bu-label\"  for=\""+this.name+"__"+cmdname+"__"+ctrl.attr("name")+"\">"+(ctrl.attr("label") || ctrl.attr("name"))+"</label>"
            tabmsg += "<input type=\"number\" id=\""+this.name+"__"+cmdname+"__"+ctrl.attr("name")+"\"";
            
            if (ctrl.attr("min")) {
                tabmsg+= " min=\""+ctrl.attr("min")+"\""
            }
            if (ctrl.attr("max")) {
                tabmsg+= " max=\""+ctrl.attr("max")+"\""
            }  
            if (classes) {
                tabmsg += " class=\"bu-spinner "+classes+"\" "
            } else {
                tabmsg += " class=\"bu-spinner\""
            }if (ctrl.attr("default")) {
                tabmsg+= " value=\""+ctrl.attr("value")+"\""
            } else {
                tabmsg+= " value=\"0\""
            }
            tabmsg+= " />"
            return ["spinner",this.name+"__"+cmdname,tabmsg];
        } else if ( ctrl.attr("type") == "date" ) { 
            if (classes) {
                tabmsg += " class=\""+classes+"\" "
            }
        } else if ( ctrl.attr("type") == "date range" ) {
            if (classes) {
                tabmsg += " class=\""+classes+"\" "
            }
        }
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
                sdiv = this.parent.removeZoneDiv(this);
            }
            this.parent = up;
            up.appendZoneDiv(this,sdiv);
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
    
    appendZoneDiv: function  (child,adiv) {
        this.children.push(child);
        var cdiv;
        if ( child.div == true ) {
            cdiv = adiv;
        } else {
            cdiv=this.addZoneDiv(child);
            child.div=true;
        }
        $("#"+this.name).append(cdiv);
        this.refresh();
    },
    
    addZoneDiv: function(child) {
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
                buddy.dropZone(event,ui,this);
            }
        });
        cdiv.dblclick(this.zoneDblClick);
        return cdiv
    },
     
    removeZoneDiv: function (child) {
        $child=$("#"+child.name);
        var sdiv = $child.detach();
        this.children=this.children.filter( function (i) {
            return i != child
        })
        this.refresh()
        return sdiv
   },
     
    destroyZone: function () {
        $.each(this.children,function(key,val) {
            val.destroyZone()
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
                    buddy.dropZone(event,ui,this);
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
            $(".bu-zonelabel").click(zoneById[buddy.currenttop].zoneClick);
            this.refresh();
        }
     },
     
    rebuild_children: function () {
        for (var i=0; i < this.children.length; i++) {
            $("#"+this.name).append(this.addZoneDiv(this.children[i]));
            this.children[i].rebuild_children();
        }
    
        for (var i=0; i < this.devices.length; i++) {
            $("#"+this.name).append(this.devices[i].addDeviceDiv());
            this.devices[i].matchStatus();
        }
     },
     
    build_children: function (children) {
        var memyself=this;
        $.each(children,function(key,val) {
            if ( val["name"] ) {
                var nz = buddy.addZone(val["nickname"],memyself,val["name"]);
            } else {
                var nz = buddy.addZone(val["name"],memyself);
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
    
    zoneDblClick: function() {
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
                        var token = buddy.sendRequest("zone nickname", "control.zone", buddy.subject,{"name":oname,"nickname": result},[oname]);
                        buddy.tokento[token]=setTimeout($.proxy(buddy.nhZNaming, buddy, token, zoneById), buddy.timeout);
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
    
    zoneClick: function() {
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
                            //$("#"+oname+"-power").destroy();
                            //return false;
                        }
                    }
                }
            });
            $("#"+oname+"-power").bootstrapSwitch();
            $("#"+oname+"-power").on("switchChange.bootstrapSwitch",function (ev,state) {
                buddy.sendCommand("power",oname,otype,(state && "on") || "off",$("#"+oname+"-propagate").val()=="on")
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
        this.debug=true;
        
        this.socket.binaryType = "arraybuffer";
        this.socket.onopen = function() {
            if ( buddy.debug ) { console.log("Connected!"); }
            isopen = true;
            var uname = getCookie("buddyuser");
            var upass = getCookie("buddypass");
            if (uname) {
                if ( buddy.debug ) { console.log("Auto login On"); }
                this.autologin = true ;
                buddy.sendLogin(uname,upass);
            }
            buddy.buildLogin();
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
                        buddy.handleLogin(msg);
                    } else if ( msg.content.response ==  'system state' ) {
                        buddy.handleState(msg)
                    } else if ( msg.content.response ==  'zone creation' ) {
                        buddy.hZCreation(msg)
                    } else if ( msg.content.response ==  'zone location' ) {
                        buddy.hZLocation(msg)
                    } else if ( msg.content.response ==  'zone deletion' ) {
                        buddy.hZDeletion(msg)
                    } else if ( msg.content.response ==  'zone nickname' ) {
                        buddy.hZNaming(msg)
                    } else if ( msg.content.response ==  'device location' ) {
                        buddy.hDLocation(msg)
                    } else if ( msg.content.response ==  'define device' ) {
                        buddy.hDDefine(msg)
                    } else if ( msg.content.response ==  'save property' ) {
                        buddy.hProperty(msg)
                    }
                }
            } else if (msg.content_type == 'event' ) {
                if ( msg.content.event ==  'status' ) {
                    buddy.hEDStatus(msg);
                } else if ( msg.content.event ==  'presence' ) {
                    buddy.hEDPresence(msg);
                } else if ( msg.content.event ==  'new device' ) {
                    buddy.hEDNew(msg);
                } else if ( msg.content.event ==  'nickname' ) {
                    buddy.hEDNickname(msg);
                } else if ( msg.content.event ==  'state change' ) {
                    buddy.hEDState(msg);
                } else if ( msg.content.event ==  'device location' ) {
                    buddy.hEDLocation(msg)
                } else if ( msg.content.event ==  'zone creation' ) {
                    buddy.hEZCreation(msg)
                } else if ( msg.content.event ==  'zone location' ) {
                    buddy.hEZLocation(msg)
                } else if ( msg.content.event ==  'zone deletion' ) {
                    buddy.hEZDeletion(msg)
                } else if ( msg.content.event ==  'zone nickname' ) {
                    buddy.hEZNaming(msg)
                } else if ( msg.content.event ==  'gui info' ) {
                    buddy.hEGInfo(msg)
                }
            }
        }
        this.socket.onclose = function(e) {
            if ( buddy.debug ) { console.log("Connection closed."); }
            this.socket = null;
            this.isopen = false;
        }
    },
    
    handleLogin: function (msg) {
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
                setCookie('buddyuser',$("#inputName").val());
                setCookie('buddypass',$("#inputPassword").val())
            }
            if ( $("#inputName").val() == "" ) {
                this.user = getCookie("buddyuser");
                this.pass = getCookie("buddypass");
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
            buddy.buildPanel();
        }
    },
    
    nhLogin: function (token) {
    },
    
    handleState: function (msg) {
        if ( msg.content.status == 'failed' ) {
            /*Display something silly*/
        } else {
            var tzone=msg.content["value"]["sub_zone"][0] /* There should only be one...should we check? */
            var topzone=buddy.addZone(tzone["nickname"],"",tzone["name"]);
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
            $('[data-toggle="tooltip"]').tooltip({placement : 'top'});
            $(window).resize(function() {
                $("#"+buddy.currenttop).css("width",$("#bu-topzonec").innerWidth());
                $("#"+buddy.currenttop).css("height",$("#bu-topzonec").innerHeight());
                zoneById[buddy.currenttop].refresh();
            });
            /*Build the menu */
            if (this.isadmin) {
                var nelt = $('<li/>');
                nelt.append($('<button/>',{ class: "btn btn-default navbar-btn", onclick:"buddy.editMode(!buddy.editmode);", html:"Edit Mode", id:"editModeButton"}));
                nelt.append($('<label/>', {for: "editModeButton", class: "sr-only", html:"Toggle Edit mode"}));
                $('#bu-navbar').append(nelt);
                nelt = $('<li/>');
                var pelt = $('<p/>', {class: "nav navbar-text zonedroppable bu-admin-menu", html:"New Zone", id:"bu-addZone"});
                pelt.draggable( {helper: "clone", revert: "invalid", zIndex: 100 })
                pelt.draggable("disable");
                pelt.hide();
                nelt.append(pelt);
                $('#bu-navbar').append(nelt);
                nelt = $('<li/>');
                pelt = $('<span/>', {class: "nav navbar-text bu-admin-menu", html:"<i class=\"fa fa-trash-o fa-lg\"></i> Delete", id:"bu-delZone"});
                /*pelt.append($("<i/>",{class: "fa fa-trash-o fa-lg"}))*/
                pelt.droppable({
                    accept: ".bu-zone",
                    greedy:true,
                    activeClass: "ui-state-default",
                    hoverClass: "ui-state-hover",
                    tolerance:"pointer",
                    drop: function( event, ui ) {
                        buddy.dropdelZone(event,ui,this);
                    }
                });
                pelt.hide();
                nelt.append(pelt);
                $('#bu-navbar').append(nelt);
                nelt = $('<li/>');
                pelt=$('<button/>',{ class: "btn btn-default navbar-btn bu-admin-menu", onclick:"manageUsers();", html:"Manage Users", id:"manageUsers"});
                nelt.append($('<label/>', {for: "manageUsers", class: "sr-only", html:"Manage Users"}));
                pelt.hide();
                nelt.append(pelt);
                $('#bu-navbar').append(nelt);
            }
            topzone.refresh();
            this.editMode(this.editmode);
            $.each(deviceById,function(idx,device) {
                buddy.sendCommand("status",device.name,device.type,"")
            })
            $(".bu-zonelabel").click(zoneById[buddy.currenttop].zoneClick);
                
        }
    },
    
    nhState: function (token) {
    },
     
    sendLogin: function (user,passwd) {
        var msg = new BuddyMsg("control.login","request");
        msg.content.request = "login";
        msg.content.target = this.subject;
        msg.content.user = user;
        msg.content.password = passwd;
        this.tokens.push(msg.content.token);
        this.socket.send(msg.json());
    },
 
    sendCommand: function (command,target, sendto, value,propagate,targetonly,options) {
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
    
    sendRequest: function (request,target, device, value, tovalue) {
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
    
    buildLogin:  function () {
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
                buddy.sendLogin($("#inputName").val(),$("#inputPassword").val());  
                $(".form-signin :input").attr("disabled", true);
            });
        
    },
    
    buildPanel: function() {
        $('#top-container').append($('<div/>', {class: "no-gutter col-xs-12 col-md-12", id: "bu-topzonec"}));
        //var ctrldiv=$('<div/>',{ class: "col-md-4", id: "bu-tools" });
        //ctrldiv.append($('<div/>', {class: "bu-nldevs", id: "bu-nldevs"}));
        //ctrldiv.append($('<div/>', {class: "bu-controls ", id: "bu-controls"}));
        //$('#top-container').append(ctrldiv);
        var zinfo=""
        if (this.topzone) {
            zinfo={"zone":this.topzone}
        }
            
        var token = this.sendRequest("system state","control", "gui",zinfo );
    },
         
    addZone: function (nickname,parent,name) {
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
        this.editMode(this.editmode)
        zoneById[nz.name]=nz;
        return nz;
    },
    
    dropZone: function (event,ui,dropin) {
        $(ui.draggable).css({left:'auto',top:"auto"}); 
        if (ui.draggable[0].id == "bu-addZone") {
            var pname = zoneById[dropin.id].name;
            var nzname="zone-"+Math.random().toString(36).substr(2);
            var token = this.sendRequest("zone creation", "control.zone", this.subject, {"parent":pname,"name":nzname, "nickname":nznametmpl+this.zonecnt},[dropin.id]);
            this.zonecnt++;
            this.tokento[token]=setTimeout($.proxy(buddy.nhZCreation, buddy, token, zoneById), this.timeout);
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
                    var token = this.sendRequest("device location", "control.zone", this.subject,{"name":name,"parent": pname},[ui.draggable[0].id,dropin.id]);
                    this.tokento[token]=setTimeout($.proxy(buddy.nhDLocation, buddy, token, deviceById), this.timeout);
                }
                
            } else {
                //A zone
                var opname = zoneById[ui.draggable[0].id].parent.name;
                var name = zoneById[ui.draggable[0].id].name;
                var pname = zoneById[dropin.id].name;
                if ( opname != pname ) {
                    var token = this.sendRequest("zone location", "control.zone", this.subject,{"name":name,"parent": pname},[ui.draggable[0].id,dropin.id]);
                    this.tokento[token]=setTimeout($.proxy(buddy.nhZLocation, buddy, token, zoneById), this.timeout);
                }
            }
        } 
    },
         
    hZNaming: function(msg) {
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
         
    hEZNaming: function(msg) {
        var type=msg.subject.split(".")[0];
        if (type == "zone") {
            var zid=msg.subject.split(".")[1];
            if ( zid in zoneById) {
                var nickname=msg.content.value["nickname"]
                zoneById[zid].nickname=nickname;
                $("#"+zid+" .bu-zonelabel").first().html("Zone "+nickname);
            }
        }
    },
    
    nhZNaming: function (token) {
        if ( this.tokeninfo[token]) {
            var nzname = "Zone "+zoneById[this.tokeninfo[token][0]].nickname;
            delete this.tokeninfo[token];
        } else {
            var nzname = "Zone";
        }
        bootbox.alert(nzname+" could not be renamed.");
    },
    
    hZLocation: function(msg) {
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
    
    hEZLocation: function(msg) {
        var type=msg.subject.split(".")[0];
        if (type == "zone") {
            var zid=msg.subject.split(".")[1];
            
            if ( zid in zoneById) {
                var pid = msg.content.value["parent"];
                zoneById[zid].set_parent(zoneById[pid]);
                zoneById[pid].refresh();
            }
        }
    },
    
    nhZLocation: function (token) {
        if ( this.tokeninfo[token]) {
            var nzname = "Zone "+this.tokeninfo[token][0];
            delete this.tokeninfo[token];
        } else {
            var nzname = "Zone";
        }
        bootbox.alert(nzname+" could not be moved.");
    },
    
    hZCreation: function(msg) {
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
    
    hEZCreation: function(msg) {
        var type=msg.subject.split(".")[0];
        if (type == "zone") {
            var zid=msg.subject.split(".")[1];
            var pid = msg.content.value["parent"];
            var nickname = msg.content.value["nickname"];
            if ( zoneById[zid] === undefined ) {
                var nz=buddy.addZone(nickname,zoneById[pid],zid);
            }
        }
    },
       
    nhZCreation: function (token) {
        if ( this.tokeninfo[token]) {
            var nzname = "New Zone in "+this.tokeninfo[token][0];
            delete this.tokeninfo[token];
        } else {
            var nzname = "New Zone";
        }
        bootbox.alert(nzname+" could not be created.");
    },
    
    deleteZone: function(name) {
        if ( buddy.debug ) { console.log("Deleting "+name); }
        var token = this.sendRequest("zone deletion", "control.zone", this.subject, {"name":name},name);
        this.tokento[token]=setTimeout($.proxy(buddy.nhZDeletion, buddy, token, zoneById), this.timeout);
    },
    
    dropdelZone: function (event,ui,dropin) {
        $(ui.draggable).addClass('drag-revert');
        $(ui.draggable).hide();
        this.deleteZone(zoneById[ui.draggable[0].id].name);
    },
     
    hZDeletion: function(msg) {
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
    
    hEZDeletion: function(msg) {
        var type=msg.subject.split(".")[0];
        if (type == "zone") {
            var zonename=msg.subject.split(".")[1];
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
                zoneById[zonename].destroyZone();
                zoneById[this.currenttop].refresh()
            }
        }
    },
       
    nhZDeletion: function (token, zoneById) {
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
    
    editMode: function(mode) {
         if (mode) {
             $('#bu-topzone').droppable("enable");
             $('.bu-zone').droppable("enable");
             $('.bu-zone').draggable("enable");
             $('.bu-device').draggable("enable");
             $("#editModeButton").addClass("btn-primary");
             $('#bu-addZone').draggable("enable");
             $('#bu-navbar .bu-admin-menu').show()
//              $('#bu-addZone').show();
//              $('#bu-delZone').show();
         } else {
             $('#bu-topzone').droppable("disable");
             $('.bu-zone').droppable("disable");
             $('.bu-zone').draggable("disable");
             $('.bu-device').draggable("disable");
             $("#editModeButton").removeClass("btn-primary");
             $('#bu-addZone').draggable("disable");
             $('#bu-navbar .bu-admin-menu').hide()
//              $('#bu-addZone').hide();
//              $('#bu-delZone').hide();
         };
         this.editmode=mode;
     },

    hEDStatus: function(msg) {
        var type=msg.subject.split(".")[0];
        var device=msg.subject.split(".")[1];
        if (deviceById[device]) {
            if (deviceById[device].type==type) {
                deviceById[device].presence=true;
                $.each(msg.content.value,function(key,value) {
                    deviceById[device].status[key]=value;
                })
            }
            deviceById[device].matchStatus();
        }
    },
    
    hEDPresence: function(msg) {
        var type=msg.subject.split(".")[0];
        var device=msg.subject.split(".")[1];
        if ( deviceById[device]) {
             if ( deviceById[device].type == type ) {
                deviceById[device].presence= ( msg.content.value == "online" )
                if ( msg.content.value == "online" ) {
                    buddy.sendCommand("status",deviceById[device].name,deviceById[device].type,"");
                } else {
                    deviceById[device].matchStatus();
                }
            }
        }
    },
    
    hEDNew: function(msg) {
        var type=msg.subject.split(".")[0];
        var device=msg.subject.split(".")[1];
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
    
    hDLocation: function(msg) {
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
    
    hEDLocation: function(msg) {
        var type=msg.subject.split(".")[0];
        var device=msg.subject.split(".")[1];
        var parent=msg.content.value["parent"];
        if ( deviceById[device] ) {
            deviceById[device].set_parent(zoneById[parent]);
            zoneById[parent].refresh();
        } else {
            var token = this.sendRequest("define device", "control.zone", this.subject,{"name":name});
        }
    },
    
    nhDLocation: function(token) {
        if ( this.tokeninfo[token]) {
            var nzname = "Device "+this.tokeninfo[token][0];
            delete this.tokeninfo[token];
        } else {
            var nzname = "Device";
        }
        bootbox.alert(nzname+" could not be moved.");
    },
   
    hDDefine: function(msg) {
        if ( msg.content.status == 'done' ) {
            var type=msg.subject.split(".")[0];
            var device=msg.subject.split(".")[1];
            if (! deviceById[device]) {
                var adevice=new BuddyDevice(msg.content.value["type"],msg.content.value["subtype"],msg.content.value["nickname"],msg.content.value["name"]);
                adevice.set_parent(zoneById[msg.content.value["parent"]])
                deviceById[adevice.name]=adevice
                $('[data-toggle="tooltip"]').tooltip({placement : 'top'});
            }
        }
    },
    
    hEDNickname: function(msg) {
        var type=msg.subject.split(".")[0];
        var device=msg.subject.split(".")[1];
        if ( deviceById[device]) {
             if ( deviceById[device].type == type ) {
                deviceById[device].nickname= msg.content.value;
                $("#"+deviceById[device].name).attr('data-original-title', msg.content.value).tooltip('fixTitle')
            }
        }
    },
    
    hEDState: function(msg) {
        var type=msg.subject.split(".")[0];
        var device=msg.subject.split(".")[1];
        if ( deviceById[device]) {
             if ( deviceById[device].type == type ) {
                deviceById[device].status[msg.content.target] = msg.content.value;
                deviceById[device].matchStatus(msg.content.target);
            }
        }
    },
    
    hProperty: function(msg) {
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
    
    nhProperty: function(token) {
        if ( this.tokeninfo[token] && this.tokeninfo[token][0]) {
            var infoname = this.tokeninfo[token][0];
            delete this.tokeninfo[token];
        } else {
            var infoname = "Information could not be saved.";
        }
        bootbox.alert(infoname);
    },

    hEGInfo: function(msg) {
        var dev=msg.subject.split(".")[0];
        var type=msg.subject.split(".")[1];
        if (msg.content["about"]) {
            $.each(msg.content["about"], function(key,val) {
                    abouttext[key]=val;
            })
        }
    },
    
})