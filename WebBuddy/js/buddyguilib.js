/*!
 * AutoBuddy JavaScript Library v0.1
 * 

 * Copyright 2016 François Wautier
 * Released under the MIT license
 *
 * Date: 2016-12-12   First baby steps 
*/

//A 
var buwidgetRegistry = {};

var buddyPanel = Class.extend({
    init: function (ctxname, xmldef, realtime) {
        // Build a panel
        // Elt is the object on behalf of which we do this
        // Def is a parsed XML documents
        // realtime indicates whether we should try to 
        this.ctxname = ctxname.replace(/\s+/g, "_-_");
        this.def = xmldef;
        this.realtime = realtime || false;
        this.locontrols = [];
    },
    
    render: function ( what ) {
        var ctxname=this.ctxname;
        var dotabs = this.def.find(what).children().length >1;
        if ( dotabs ) {
            var msg = "<ul class=\"nav nav-tabs\">";
            var tabmsg = "<div id=\""+ctxname+"-tab-content\" class=\"tab-content\">";
        } else {
            var tabmsg = "<div id=\""+ctxname+"-top-level\" >";
        }
        var realtime = this.realtime;
        var locontrols = this.locontrols;
        if (what === undefined) {
            // If undefined, first child is active
            what = "command";
        }
        var active = true;
        $.each(this.def.find(what), function (idx, tpart) {
            $.each($(tpart).children(),  function (idx, part) {
                var lbl = $(part).attr("label") || $(part).attr("name");
                var cname = $(part).attr("name").replace(/\s+/g, "_-_");
                if ( dotabs ) {
                    if ( active ) {
                        active=false;
                        msg+="<li role=\"presentation\" class=\"bu-commandtab active\"><a href=\"#"+ctxname+"-"+cname+
                            "\"  data-toggle=\"tab\">"+lbl+"</a></li>\n";
                        tabmsg+="<div class=\"tab-pane bu-commandpanel active\" id=\""+ctxname+"-"+cname+"\">\n";
                    } else {
                        msg+="<li role=\"presentation\" class=\"bu-commandtab\"><a href=\"#"+ctxname+"-"+cname+
                            "\"  data-toggle=\"tab\">"+lbl+"</a></li>\n";
                        tabmsg+="</div><div class=\"tab-pane bu-commandpanel\" id=\""+ctxname+"-"+cname+"\">\n";
                    }
                }
                if ( $(part).is("controlgroup") ) {
                    var ncg = false;
                    if ( $(part).attr("type") == "list" ) {
                        ncg = new listCG(ctxname,cname,$(part), realtime)
                    } else if ( $(part).attr("type") == "grouplist" ) {
                        ncg = new grouplistCG(ctxname,cname,$(part), realtime)
                    } else if ( $(part).attr("type") == "choice" ) {
                        ncg = new choiceCG(ctxname,cname,$(part), realtime)
                    } else if ( $(part).attr("type") == "listmaker" ) {
                        ncg = new listmakerCG(ctxname,cname,$(part), realtime)
                    } else {
                        console.log("Unknown controlgroup type "+$(part).attr("type"))
                        return "";
                    }
                    if ( ncg ) {
                        tabmsg+=ncg.render();
                        locontrols.push(ncg)
                    }
                } else if ( $(part).is("control") ) {
                    var nco = false;
                    if ( $(part).attr("type") == "slider" ) {
                        nco = new sliderControl(ctxname,cname,$(part),realtime)
                        tabmsg+=nco.render();
                    } else if  ( $(part).attr("type") == "knob" ) {
                        nco = new knobControl(ctxname,cname,$(part),realtime)
                        tabmsg+=nco.render();
                    } else if   ( $(part).attr("type") == "spinner" ) {
                        nco = new spinnerControl(ctxname,cname,$(part),realtime)
                        tabmsg+=nco.render();
                    } else if   ( $(part).attr("type") == "switch" ) {
                        nco = new switchControl(ctxname,cname,$(part),realtime)
                        tabmsg+=nco.render();
                    } else if   ( $(part).attr("type") == "time" ) {
                        nco = new switchControl(ctxname,cname,$(part),realtime)
                        tabmsg+=nco.render();
                    } else if   ( $(part).attr("type") == "time range" ) {
                        nco = new switchControl(ctxname,cname,$(part),realtime)
                        tabmsg+=nco.render();
                    } else if   ( $(actrl).attr("type") == "text" ) {
                        nco = new textControl(ctxname,cname,$(part),realtime)
                        tabmsg+=nco.render();
                    } else {
                        console.log("Unknown control type " + $(part).attr("type") )
                    }
                    if ( nco ) {
                        locontrols.push(nco)
                    }
                        
                }
            })
        })
        if ( dotabs ) {
            msg+="</ul>"+tabmsg+"</div></div>";
        } else { 
            msg=tabmsg+"</div>";
        }
        return msg;
    },
    
    activate: function(size) {
        $.each(this.locontrols, function (elt, actrl) {
            actrl.activate(size);
            });
    },
    
    setCallback: function(callback) {
        $.each(this.locontrols, function (elt, actrl) {
            actrl.setCallback(callback);
        });
    },
    
    getValue: function() {

        var resu={};
        var self = this;
        $.each(this.locontrols, function (idx, actrl) {
            var aval = actrl.getValue();
            var zz = {};
            if ( $.isPlainObject(aval) && actrl.part.attr("name") in aval ) {
                zz = aval;
            } else {
                zz[actrl.part.attr("name")] = actrl.getValue();
            }
            zz = $.extend(resu,zz);
        })
        return resu
    },
    
    setValue: function(vals) {
        $.each(this.locontrols, function (idx, actrl) {
            actrl.setValue(vals);
        })
    }
})

var listCG = Class.extend({
    init: function (ctxname, pname,part, realtime) {
        // Build a panel
        // Elt is the object on behalf of which we do this
        // Def is a parsed XML documents
        this.ctxname = ctxname;
        this.pname = pname;
        this.part = part;
        this.realtime = realtime || false;
        this.jsid = this.ctxname.replace(/\s+/g, "_-_");
        this.newctxname =  this.ctxname.replace(/\s+/g, "_-_")
        if ( this.pname ) {
            this.jsid += "__"+this.pname.replace(/\s+/g, "_-_");
            this.newctxname += "__"+this.pname.replace(/\s+/g, "_-_");
        }
        this.jsid += "__"+this.part.attr("name").replace(/\s+/g, "_-_")+"_list";
        this.widget_name = undefined;
        this.widget = undefined;
        this.locontrols = [];
        this.paramlist = [];
    },
    
    render: function (classes) {
        var tabmsg = "";
        var self = this;
        if (this.part.attr("widget") && this.part.attr("widget") in buwidgetRegistry) {
            this.widget_name = this.part.attr("widget")
            tabmsg += "<div id=\""+this.jsid+"\"";
            tabmsg += " class=\"bu-widget bu-widget-"+this.part.attr("widget")
            if ( classes != undefined ) { 
                tabmsg += classes;
            }
            tabmsg += "\" paramlist=\"";
            var sep="";
            $.each($(this.part).children(),  function (idx, part) {
                if ( $(part).attr("name") !== undefined ) {
                    tabmsg +=sep+$(part).attr("name");
                    self.paramlist.push($(part).attr("name"));
                    sep=",";
                }
            })
            tabmsg += "\" />";
        } else {
            var ctxname = this.newctxname;
            var cname = this.pname;
            var realtime = this.realtime;
            var locontrols = this.locontrols;
            var ctxname = this.ctxname;
            var tabstr=undefined;
            var active=true;
            $.each(this.part.children(), function (jdx, actrl) {
                if ($(actrl).is("[newtab=\"true\"]")) {
                    if ( active ) {
                        active=false;
                        tabstr= tabmsg+"<ul class=\"nav nav-tabs\">";
                        tabmsg = "<div id=\""+ctxname+"-tab-content\" class=\"tab-content\">";
                        tabstr+="<li role=\"presentation\" class=\"bu-commandtab active\"><a href=\"#"+ctxname+"-"+cname+"-"+
                            $(actrl).attr("name")+"-tab-pane\"  data-toggle=\"tab\">"+$(actrl).attr("label")||$(actrl).attr("name")+"</a></li>\n";
                        tabmsg+="<div class=\"tab-pane bu-commandpanel active\" id=\""+ctxname+"-"+cname+"-"+
                            $(actrl).attr("name")+"-tab-pane\" >\n";
                    } else {
                        tabstr+="<li role=\"presentation\" class=\"bu-commandtab\"><a href=\"#"+ctxname+"-"+cname+"-"+
                            $(actrl).attr("name")+"-tab-pane\"  data-toggle=\"tab\">"+$(actrl).attr("label")||$(actrl).attr("name")+"</a></li>\n";
                        tabmsg+="</div><div class=\"tab-pane bu-commandpanel\" id=\""+ctxname+"-"+cname+"-"+
                            $(actrl).attr("name")+"-tab-pane\" >\n";
                    }
                }
                if ( $(actrl).is("controlgroup") ) {
                    var ncg = false;
                    if ( $(actrl).attr("type") == "list" ) {
                        ncg = new listCG(ctxname,cname,$(actrl), realtime)
                    } else if ( $(actrl).attr("type") == "grouplist" ) {
                        ncg = new grouplistCG(ctxname,cname,$(actrl), realtime)
                    } else if ( $(actrl).attr("type") == "choice" ) {
                        ncg = new choiceCG(ctxname,cname,$(actrl), realtime)
                    } else if ( $(actrl).attr("type") == "listmaker" ) {
                        ncg = new listmakerCG(ctxname,cname,$(actrl), realtime)
                    }
                    if ( ncg ) {
                        tabmsg+=ncg.render(classes);
                        locontrols.push(ncg)
                    }
                } else if ( $(actrl).is("control") ) {
                    var nco = false;
                    if ( $(actrl).attr("type") == "slider" ) {
                        nco = new sliderControl(ctxname,cname,$(actrl),realtime)
                        tabmsg+=nco.render(classes);
                    } else if  ( $(actrl).attr("type") == "knob" ) {
                        nco = new knobControl(ctxname,cname,$(actrl),realtime)
                        tabmsg+=nco.render(classes);
                    } else if   ( $(actrl).attr("type") == "spinner" ) {
                        nco = new spinnerControl(ctxname,cname,$(actrl),realtime)
                        tabmsg+=nco.render(classes);
                    } else if   ( $(actrl).attr("type") == "switch" ) {
                        nco = new switchControl(ctxname,cname,$(actrl),realtime)
                        tabmsg+=nco.render(classes);
                    } else if   ( $(actrl).attr("type") == "time" ) {
                        nco = new timeControl(ctxname,cname,$(actrl),realtime)
                        tabmsg+=nco.render(classes);
                    } else if   ( $(actrl).attr("type") == "time range" ) {
                        nco = new timerangeControl(ctxname,cname,$(actrl),realtime)
                        tabmsg+=nco.render(classes);
                    } else if   ( $(actrl).attr("type") == "date" ) {
                        nco = new dateControl(ctxname,cname,$(actrl),realtime)
                        tabmsg+=nco.render(classes);
                    } else if   ( $(actrl).attr("type") == "text" ) {
                        nco = new textControl(ctxname,cname,$(actrl),realtime)
                        tabmsg+=nco.render(classes);
                    } else {
                        console.log("Unknown control type " + $(actrl).attr("type") )
                    }
                    if ( nco ) {
                        locontrols.push(nco)
                    }
                }
            })
            if ( !active ) {
                tabmsg=tabstr+"</ul>"+tabmsg+"</div>";
            }
        }
        return tabmsg;
    },
            
    activate: function( size) {
         //size is an array with 2 values, 
         // call back is an actual call back for widget, True or false otherwise
         if ( this.widget_name ) {
             if ( this.widget == undefined ) {
                this.widget = new buwidgetRegistry[this.widget_name]($("#"+this.jsid)[0],size[0],size[1])
             }
         } else { 
            $.each(this.locontrols, function (elt, actrl) {
                actrl.activate(size);
            });
        }
        $("#"+this.jsid).data("buguiObj",this);    
    },
    
    setCallback: function( callback) {
         if ( this.widget_name ) {
             if ( this.realtime && this.part.attr("rteffect") ) {
                 this.widget.onChange(callback);
             } 
         } else { 
            $.each(this.locontrols, function (elt, actrl) {
                actrl.setCallback(callback);
            });
        }
    },
    
    getValue: function() {

        var resu={};
        var self = this;
        if ( this.widget_name ) {
            resu = this.widget.getValue();
        } else {
            $.each(this.locontrols, function (idx, actrl) {
                var zz = {};
                var aval = actrl.getValue();
                if ( actrl.widget_name || ( $.isPlainObject(aval) && actrl.part.attr("name") in aval && Object.keys(aval).length <= 1)) {
                    zz=$.extend(resu,aval)
                } else {
                    zz[actrl.part.attr("name")] = aval;
                }
                    
                zz=$.extend(resu,zz);
            })
        }
        var r = {};
        if ( self.part.attr("name") in resu ) {
            if ( resu.length <= 1 ) {
                return resu;
            } else if ( ! ( $.isNumeric(resu[self.part.attr("name")]) || 
                            $.type(resu[self.part.attr("name")]) === "string" ||
                            $.isArray(resu[self.part.attr("name")]) ||
                            $.type(resu[self.part.attr("name")]) === "boolean" ) ) {
                var tmp = resu[self.part.attr("name")];
                delete resu[self.part.attr("name")];
                tmp=$.extend(resu,tmp);
            
            }
                           
        }
        r[self.part.attr("name")] = resu;
        return r;
    },
    
    setValue: function(vals) {
        var thiscmd = this.part.attr("name")
        var self = this;
        if ( thiscmd in vals ) {
            if ( this.widget_name ) {
                resu = this.widget.setValue(vals[thiscmd]);
            } else {
                $.each(this.locontrols, function (idx, actrl) {
                    if ( actrl.widget_name ) {
                        if ( actrl.part.attr("name") ==  thiscmd ){
                            actrl.widget.setValue(vals[thiscmd]);
                        } else if ( actrl.part.attr("name") in vals[thiscmd] ) {
                            actrl.widget.setValue(vals[thiscmd][actrl.part.attr("name")]);
                        }
                    } else {
                        actrl.setValue(vals[thiscmd]);
                    }
                })
            }
        }
    },
    
    resetMe: function() {
        $.each(this.locontrols, function (idx, actrl) {
            actrl.resetMe();
        })
    }
})


var grouplistCG = Class.extend({
    init: function (ctxname, pname,part, realtime) {
        // Build a panel
        // Elt is the object on behalf of which we do this
        // Def is a parsed XML documents
        this.ctxname = ctxname;
        this.pname = pname;
        this.part = part;
        this.realtime=realtime || false
        this.list= new listCG(ctxname,pname,part, false)
        this.jsid = this.ctxname.replace(/\s+/g, "_-_");
        if ( this.pname ) {
            this.jsid += "__"+this.pname.replace(/\s+/g, "_-_");
            this.newctxname += "__"+this.pname.replace(/\s+/g, "_-_");
        }
        this.jsid += "__"+this.part.attr("name").replace(/\s+/g, "_-_")+"__groupdiv";
    },
    
    render: function (classes) {
        if ( this.realtime ) {
            tabmsg = "<div id=\""+this.jsid+"\" class=\"bu-grouplist\">";
            tabmsg +=this.list.render(classes)
            tabmsg += "<div><input style=\"margin-left:20px; margin-right: 20px; margin-top: 30px;\" id=\""+this.jsid+"__bapply\" class=\"btn btn-primary\" type=\"button\" value=\""+(this.part.attr("label")||"Apply")+"\"></div></div>";
        } else {
            tabmsg=this.list.render(classes)
        }
        return tabmsg;
    },
            
    activate: function( size) {
         //size is an array with 2 values, 
         // call back is an actual call back for widget, True or false otherwise
        this.list.activate(size)
        if (this.realtime) {
            
            $("#"+this.jsid).data("buguiObj",this);
        }
    },
    
    setCallback: function( callback) {
        $("#"+this.jsid+"__bapply").on("click", callback);
    },
    
    getValue: function() {

       return this.list.getValue()
    },
    
    setValue: function(vals) {
        this.list.setValue(vals)
    },
    
    resetMe: function() {
        this.list.resetMe()
    }
})




var listmakerCG = Class.extend({
    init: function (ctxname, pname,part, realtime) {
        // Build a panel
        // Elt is the object on behalf of which we do this
        // Def is a parsed XML documents
        this.ctxname = ctxname;
        this.pname = pname;
        this.part = part;
        this.realtime = realtime || false;
        this.jsid = this.ctxname.replace(/\s+/g, "_-_");
        this.newctxname =  this.ctxname.replace(/\s+/g, "_-_");
        if ( this.pname ) {
            this.jsid += "__"+this.pname.replace(/\s+/g, "_-_");
            this.newctxname += "__"+this.pname.replace(/\s+/g, "_-_");
        }
        this.jsid += "__"+this.part.attr("name").replace(/\s+/g, "_-_");
        this.locontrols = [];
        this.listvals = {};
        if ( this.part.attr("key") ) {
            this.key = this.part.attr("key");
        } else {
            this.callback = undefined;
        }
        this.size=null
        this.lotab=[];
        if ( this.part.attr("dfltname") ) {
            this.dfltname = this.part.attr("dfltname");
        } else {
            this.dfltname = undefined;
        }
        this.dnidx = 0;
    },
    
    genname: function () {
        if (this.dfltname == undefined ) {
            this.dfltname=this.key;
        }
        var newname = this.dfltname + " "+this.dnidx;
        this.dnidx+=1;
        while ( newname in this.listvals ) {
            newname = this.dfltname + " "+this.dnidx;
            this.dnidx+=1;
        }
        return newname;
    },
    
    render: function (classes) {
        var tabmsg = "";
        var self = this;
        var ctxname = this.newctxname;
        var cname = this.pname;
        var realtime = this.realtime;
        var locontrols = this.locontrols;
        tabmsg += "<div id=\""+this.jsid+"_bulmdiv\"";
        if ( classes != undefined ) { 
            tabmsg += " class=\""+classes+"\" ";
        }
        tabmsg += ">"
        if ( this.part.attr("label") ) {
            tabmsg += "<label class=\"bu-label\"  for=\""+this.jsid+"__selector\">"+this.part.attr("label")+"</label>"
        }
        tabmsg += "<select class=\"selectpicker\" data-width=\"fit\" id=\""+this.jsid+"__selector\" >";
        tabmsg += "<option value=\"bulmknew\" >Add New</option>";
        tabmsg += "</select></div>";
        tabmsg += "<div id=\""+this.jsid+"_budiv\"";
        if ( classes != undefined ) { 
            tabmsg += " class=\""+classes+"\" ";
        }
        tabmsg += ">"
        var tabstr=undefined;
        var active=true;
        $.each(this.part.children(), function (jdx, actrl) {
            if ($(actrl).is("[newtab=\"true\"]")) {
                if ( active) {
                    active=false;
                    tabstr= tabmsg+"<ul class=\"nav nav-tabs\">";
                    tabmsg = "<div id=\""+ctxname+"-tab-content\" class=\"tab-content\">";
                    tabstr+="<li role=\"presentation\" class=\"bu-commandtab active\"><a href=\"#"+ctxname+"-"+cname+"-"+
                        $(actrl).attr("name")+"-tab-pane\"  data-toggle=\"tab\">"+$(actrl).attr("label")||$(actrl).attr("name")+"</a></li>\n";
                    tabmsg+="<div class=\"tab-pane bu-commandpanel active\" id=\""+ctxname+"-"+cname+"-"+
                        $(actrl).attr("name")+"-tab-pane\" >\n";
                } else {
                    tabstr+="<li role=\"presentation\" class=\"bu-commandtab\"><a href=\"#"+ctxname+"-"+cname+"-"+
                        $(actrl).attr("name")+"-tab-pane\"  data-toggle=\"tab\">"+$(actrl).attr("label")||$(actrl).attr("name")+"</a></li>\n";
                    tabmsg+="</div><div class=\"tab-pane bu-commandpanel\" id=\""+ctxname+"-"+cname+"-"+
                        $(actrl).attr("name")+"-tab-pane\" >\n";
                }
                self.lotab.push("#"+ctxname+"-"+cname+"-"+$(actrl).attr("name")+"-tab-pane");
            }
            if ( $(actrl).is("controlgroup") ) {
                var ncg = false; 
                if ( $(actrl).attr("type") == "list" ) {
                    ncg = new listCG(ctxname,cname,$(actrl), realtime)
                    } else if ( $(actrl).attr("type") == "grouplist" ) {
                        ncg = new grouplistCG(ctxname,cname,$(actrl), realtime)
                } else if ( $(actrl).attr("type") == "choice" ) {
                    ncg = new choiceCG(ctxname,cname,$(actrl), realtime)
                } else if ( $(actrl).attr("type") == "listmaker" ) {
                    ncg = new listmakerCG(ctxname,cname,$(actrl), realtime)
                }
                if ( ncg ) {
                    tabmsg+=ncg.render(classes);
                    locontrols.push(ncg)
                }
            } else if ( $(actrl).is("control") ) {
                var nco = false;
                if ( $(actrl).attr("type") == "slider" ) {
                    nco = new sliderControl(ctxname,cname,$(actrl),realtime)
                    tabmsg+=nco.render(classes);
                } else if  ( $(actrl).attr("type") == "knob" ) {
                    nco = new knobControl(ctxname,cname,$(actrl),realtime)
                    tabmsg+=nco.render(classes);
                } else if   ( $(actrl).attr("type") == "spinner" ) {
                    nco = new spinnerControl(ctxname,cname,$(actrl),realtime)
                    tabmsg+=nco.render(classes);
                } else if   ( $(actrl).attr("type") == "switch" ) {
                    nco = new switchControl(ctxname,cname,$(actrl),realtime)
                    tabmsg+=nco.render(classes);
                } else if   ( $(actrl).attr("type") == "time" ) {
                    nco = new timeControl(ctxname,cname,$(actrl),realtime)
                    tabmsg+=nco.render(classes);
                } else if   ( $(actrl).attr("type") == "time range" ) {
                    nco = new timerangeControl(ctxname,cname,$(actrl),realtime)
                    tabmsg+=nco.render(classes);
                } else if   ( $(actrl).attr("type") == "date" ) {
                    nco = new dateControl(ctxname,cname,$(actrl),realtime)
                    tabmsg+=nco.render(classes);
                } else if   ( $(actrl).attr("type") == "text" ) {
                    nco = new textControl(ctxname,cname,$(actrl),realtime)
                    tabmsg+=nco.render(classes);
                } else {
                    console.log("Unknown control type " + $(actrl).attr("type") )
                }
                if ( nco ) {
                    locontrols.push(nco);
                    if ( self.key === undefined ) {
                        self.key = nco.part.attr("name");
                    }
                }
            }
        })
        if ( !active ) {
            tabmsg=tabstr+"</ul>"+tabmsg+"</div>";
        }
        tabmsg += "</div><div><input style=\"margin-left:20px; margin-right: 20px; margin-top: 30px;\" id=\""+this.jsid+"__badd\" class=\"btn btn-primary\" type=\"button\" value=\"Commit\">";
        tabmsg += "<input style=\"margin-left:20px; margin-right: 20px; margin-top: 30px;\" id=\""+this.jsid+"__bdel\"class=\"btn btn-danger\" type=\"button\" value=\"Delete\"></div> ";
        return tabmsg;
    },
            
    activate: function( size) {
         //size is an array with 2 values, 
        this.size=size
        $("#"+this.jsid+"__selector").on("changed.bs.select", this.onProxy);
        $("#"+this.jsid+"__badd").on("click", $.debounce(1,this.onProxy));
        //$("#"+this.jsid+"__badd").on("click", this.onProxy);
        $("#"+this.jsid+"__bdel").on("click", this.onProxy);
        $("#"+this.jsid+"__selector").selectpicker('val', "bulmknew");
        this.onChange();
        $("#"+this.jsid+"__selector").data("buguiObj",this);
        $("#"+this.jsid+"__badd").data("buguiObj",this);
        $("#"+this.jsid+"__bdel").data("buguiObj",this);
        $("#"+this.jsid+'_budiv').find('a[data-toggle="tab"]').on('show.bs.tab', function (e) {
            //Not sure why we must do yjis... but we must or tab and content get out of sync
            var target = $(e.relatedTarget).length;
            if ( target > 0 )  {
                return true;
            }
            return false;
        });
    },
    
    setCallback: function ( callback ) {
        this.callback = callback;
    },
    
    onProxy: function (e)  {
        var cmd = this.id.split("__").slice(-1)[0];
        var n = this.id.search("__"+cmd);
        var id = this.id.slice(0,n);
        if ( cmd == "selector" ) {
            $(this).data("buguiObj").onChange(e);
        } else if ( cmd == "badd" ) {
            $(this).data("buguiObj").onAdd(e);
        } else if( cmd == "bdel" ) {
            $(this).data("buguiObj").onDelete(e);
        } else {
            console.log("No \""+cmd+"\" button in listmaker");
        }
        return false;
    },
       
    onChange: function (e)  {
        var newval = $("#"+this.jsid+"__selector").find("option:selected").val();
        var vals = this.listvals[newval];
        var size = this.size;
        if ( vals ) {
            $.each(this.locontrols, function (elt, actrl) {
                actrl.resetMe();
                actrl.setValue(vals);
            });
        } else {
            $.each(this.locontrols, function (elt, actrl) {
                actrl.resetMe();
                actrl.activate(size);
            });
        }
        return false;
    },
    
    onAdd: function (e) {
        if ( this.callback) {
            this.callback(e);
        }
        var val = {};
        $.each(this.locontrols, function (elt, actrl) {                
            var aval = actrl.getValue();
            if ( actrl.widget_name || ( $.isPlainObject(aval) && actrl.part.attr("name") in aval && Object.keys(aval).length <= 1)) {
                var zz=$.extend(val,aval);
            } else {
                val[actrl.part.attr("name")]=aval;
            }
        });
        if ( ! val[this.key].trim() ) {
            val[this.key]=this.genname();
        }
        this.listvals[val[this.key]]=val;
        this.setValue(this.getValue());
        $("#"+this.jsid+"__selector").selectpicker('val', "bulmknew");
        $.each(this.locontrols, function (elt, actrl) {
            actrl.resetMe();
        });
        this.onChange();
        return false;
    },
    
    onDelete: function (e) {
        if ( this.callback) {
            this.callback(e);
        }
        var val = {};
        $.each(this.locontrols, function (elt, actrl) {
            val[actrl.part.attr("name")]=actrl.getValue();
        });
        if ( val[this.key] == "bulmknew" ) { return; } 
        delete this.listvals[val[this.key]];
        this.setValue(this.getValue());
        $("#"+this.jsid+"__selector").selectpicker('val', "bulmknew");
        $.each(this.locontrols, function (elt, actrl) {
            actrl.resetMe();
        });
        this.onChange();
        return false;
    },
        
    getValue: function() {
        var r = {};
        var kl = [];
        var a = [];
        var self = this;
        $.each(this.listvals, function (akey, elt) {
            if ( akey != "bulmknew" ) {
                kl.push(akey);
            }
        });
        kl.sort();

        $.each(kl, function (elt, akey) {
            a.push(self.listvals[akey]);
        });
        r[self.part.attr("name")] =a;
        return r;
    },
    
    resetMe: function() {
        this.listvals={};
        $("#"+this.jsid+"__selector").empty().append(new Option("Add New", "bulmknew"));
        $("#"+this.jsid+"__selector").selectpicker("refresh")
        $("#"+this.jsid+"__selector").selectpicker('val', "bulmknew");
    },
    
    setValue: function(vals) {
        var thiscmd = this.part.attr("name")
        var self = this;
        if ( thiscmd in vals ) {
            var kl = [];
            var klidx=0;
            var tbdel=[];
            var docheck=false; //to skip the first option
            $.each(vals[thiscmd], function (elt, aval) {
                if ( aval[self.key] != "bulmknew" ) {
                    kl.push(aval[self.key]);
                }
            });
            kl.sort();
            $.each($("#"+this.jsid+"__selector option"), function (elt, anopt) {
                if (docheck ) {
                    if ( klidx >= kl.length || anopt.value < kl[klidx] ) {
                        tbdel.push(anopt);
                    } else if ( anopt.value == kl[klidx] ) {
                        klidx++;
                    } else  {
                        for ( x=klidx; x<kl.length; x++ ) {
                            if ( anopt.value <= kl[klidx] ) {
                                if ( anopt.value == kl[klidx] ) {
                                    klidx++;
                                } else {
                                    tbdel.push(anopt);
                                }
                                break;
                            }
                            anopt.before(new Option(kl[klidx],kl[klidx]));
                            klidx++;
                            
                        }
                    }
                
                }
                docheck=true;
            }); 
            if ( klidx < kl.length) {
                for ( x=klidx; x<kl.length; x++ ) {
                    $("#"+this.jsid+"__selector").append(new Option(kl[klidx],kl[klidx]));
                    klidx++;
                }
            }
             
            $.each(tbdel, function (elt, anopt) {
                anopt.remove();
            });
            $.each(vals[thiscmd], function (elt, aval) {
                self.listvals[aval[self.key]]=aval;
            });
            $("#"+self.jsid+"__selector").selectpicker('refresh');
        }
 
    }
}) 
var choiceCG = Class.extend({
    init: function (ctxname, pname,part, realtime) {
        // Build a panel
        // Elt is the object on behalf of which we do this
        // Def is a parsed XML documents
        this.ctxname = ctxname;
        this.pname = pname;
        this.part = part;
        this.realtime = realtime || false;
        this.jsid = this.ctxname.replace(/\s+/g, "_-_");
        this.newctxname =  this.ctxname.replace(/\s+/g, "_-_");
        if ( this.pname ) {
            this.jsid += "__"+this.pname.replace(/\s+/g, "_-_");
            this.newctxname += "__"+this.pname.replace(/\s+/g, "_-_");
        }
        this.jsid += "__"+this.part.attr("name").replace(/\s+/g, "_-_");
        this.widget_name = undefined;
        this.widget = undefined;
        this.locontrols = [];
        this.itemlist = {};
        this.size = undefined;
        this.callback = undefined;
        this.afterme=undefined;
        this.subchoices=[];
        this.aboveclasses = "";
    },
    
    render: function (classes) {
        var tabmsg = "";
        var self = this;
        var locontrols = this.locontrols;
        tabmsg += "<div id=\""+this.jsid+"_budiv\"";
        if ( classes != undefined ) { 
            tabmsg += " class=\""+classes+"\" ";
            this.aboveclasses = classes;
        }
        tabmsg += ">"
        if ( this.part.attr("label") ) {
            tabmsg += "<label class=\"bu-label\"  for=\""+this.jsid+"\">"+this.part.attr("label")+"</label>";
        }
        tabmsg += "<select class=\"selectpicker\" data-width=\"fit\" id=\""+this.jsid+"\" >";
        $.each(this.part.children(), function (jdx, actrl) {
            if ( $(actrl).is("item") ) {
                tabmsg += "<option value=\""+$(actrl).attr("value")+"\" >";
                tabmsg += $(actrl).attr("label") || $(actrl).attr("value")+"</option>";
                self.itemlist[$(actrl).attr("value")] = $(actrl).children();
            } else if ( $(actrl).is("itemgroup") ) {
                tabmsg += "<optgroup label=\""+$(actrl).attr("value")+"\" />";
            } else if ( $(actrl).is("control") ) {
                console.log("Only \"item\" and \"itemgroup\" elements can appear in a \"choice\", not: "+actrl.nodeName);
            } else if ( $(actrl).is("controlgroup") ) {
                console.log("Only \"item\" and \"itemgroup\" elements can appear in a \"choice\", not: "+actrl.nodeName);
            }
        })
        tabmsg += "</select></div>";
        return tabmsg;
    },
            
    activate: function( size) {
        //size is an array with 2 values, 
        this.size = size;
        $("#"+this.jsid).on("changed.bs.select", this.proxyChange);
        var thisval = this.part.find("#"+this.jsid +" > default").text();
        if ( ! thisval ) {
            thisval=$(this.part.children()[0]).attr("value")
        }
        $("#"+this.jsid).selectpicker('val', thisval);
        this.onChange();
        $("#"+this.jsid).data("buguiObj",this);
    },
    
    setCallback: function(callback) {
        this.callback=callback;
    },
    
    proxyChange: function(e) {
        return $(this).data("buguiObj").onChange(e);
    },
    
    onChange: function (e) {
        if ( this.callback) {
            this.callback(e);
        }
        var self = this;
        $("#"+this.jsid+"_budiv").nextAll("."+this.jsid+"_added").remove();
        $.each(this.subchoices, function (jdx, achoice) {
            $("#"+self.jsid+"_budiv").nextAll("."+achoice+"_added").remove();
        });
        this.afterme=this.jsid+"_budiv";
        this.locontrols=[];
        var newval = $("#"+this.jsid).find("option:selected").val();
        $.each(this.itemlist[newval], function (jdx, actrl) {
            
            if ( $(actrl).is("controlgroup") ) {
                var ncg = false;
                if ( $(actrl).attr("type") == "list" ) {
                    ncg = new listCG(self.newctxname,self.part.attr('name'),$(actrl), self.realtime)
                } else if ( $(actrl).attr("type") == "grouplist" ) {
                    ncg = new grouplistCG(self.newctxname,self.part.attr('name'),$(actrl), self.realtime)
                } else if ( $(actrl).attr("type") == "choice" ) {
                    ncg = new choiceCG(self.newctxname,self.part.attr('name'),$(actrl), self.realtime)
                } else if ( $(actrl).attr("type") == "listmaker" ) {
                    ncg = new listmakerCG(self.newctxname,self.part.attr('name'),$(actrl), self.realtime)
                }
                if ( ncg ) {
                    $("#"+self.afterme).after(ncg.render(self.aboveclasses+ " " + self.jsid+"_added"));
                    if ( $(actrl).attr("type") == "choice" ) {
                        self.afterme = ncg.jsid+"_budiv";
                        self.subchoices.push(ncg.jsid);
                    } else if ( $(actrl).attr("type") == "listmaker" ) {
                        self.afterme = ncg.jsid+"_bulmdiv";
                        self.subchoices.push(ncg.jsid)
                    } else {
                        self.afterme = ncg.jsid;
                    }
                    self.locontrols.push(ncg);
                }
            } else if ( $(actrl).is("control") ) {
                var nco = false;
                if ( $(actrl).attr("type") == "slider" ) {
                    nco = new sliderControl(self.newctxname,self.part.attr('name'),$(actrl),self.realtime)
                    $("#"+self.afterme).after(nco.render(self.aboveclasses+ " " + self.jsid+"_added"));
                    self.afterme = nco.jsid+"_bucont";
                } else if  ( $(actrl).attr("type") == "knob" ) {
                    nco = new knobControl(self.newctxname,self.part.attr('name'),$(actrl),self.realtime)
                    $("#"+self.afterme).after(nco.render(self.aboveclasses+ " " + self.jsid+"_added"));
                    self.afterme = nco.jsid+"_bucont";
                } else if   ( $(actrl).attr("type") == "spinner" ) {
                    nco = new spinnerControl(self.newctxname,self.part.attr('name'),$(actrl),self.realtime)
                    $("#"+self.afterme).after(nco.render(self.aboveclasses+ " " + self.jsid+"_added"));
                    self.afterme = nco.jsid+"_bucont";
                } else if   ( $(actrl).attr("type") == "switch" ) {
                    nco = new switchControl(self.newctxname,self.part.attr('name'),$(actrl),self.realtime)
                    $("#"+self.afterme).after(nco.render(self.aboveclasses+ " " + self.jsid+"_added"));
                    self.afterme = nco.jsid+"_bucont";
                } else if   ( $(actrl).attr("type") == "time" ) {
                    nco = new timeControl(self.newctxname,self.part.attr('name'),$(actrl),self.realtime)
                    $("#"+self.afterme).after(nco.render(self.aboveclasses+ " " + self.jsid+"_added"));
                    self.afterme = nco.jsid+"_bucont";
                } else if   ( $(actrl).attr("type") == "time range" ) {
                    nco = new timerangeControl(self.newctxname,self.part.attr('name'),$(actrl),self.realtime)
                    $("#"+self.afterme).after(nco.render(self.aboveclasses+ " " + self.jsid+"_added"));
                    self.afterme = nco.jsid+"_bucont";
                } else if   ( $(actrl).attr("type") == "date" ) {
                    nco = new dateControl(self.newctxname,self.part.attr('name'),$(actrl),self.realtime)
                    $("#"+self.afterme).after(nco.render(self.aboveclasses+ " " + self.jsid+"_added"));
                    self.afterme = nco.jsid+"_bucont";
                } else if   ( $(actrl).attr("type") == "text" ) {
                    nco = new textControl(self.newctxname,self.part.attr('name'),$(actrl),self.realtime)
                    $("#"+self.afterme).after(nco.render(self.aboveclasses+ " " + self.jsid+"_added"));
                    self.afterme = nco.jsid+"_bucont";
                } else {
                    console.log("Unknown control type " + $(actrl).attr("type") )
                }
                if ( nco ) {
                    self.locontrols.push(nco)
                }
            }
        })
        var size=this.size;
        $.each(this.locontrols, function (elt, actrl) {
            actrl.activate(size);
        });
        return false;
    },
    
    getValue: function() {
        var resu={};
        resu[this.part.attr("name")] = {"bu-cvalue":$("#"+this.jsid).val()};
        var zz = {};
        var self = this;     

        $.each(this.locontrols, function (idx, actrl) {
            var aval = actrl.getValue();        
            if ( $.isPlainObject(aval) && actrl.part.attr("name") in aval ) {
                zz = aval;
            } else {
                zz[actrl.part.attr("name")] = actrl.getValue();
            }
            if ( actrl.pname in resu) {
                zz = $.extend(resu[actrl.pname],zz);
            } else {
                zz = $.extend(resu,zz)
            }
        })
        return resu;
    },

    setValue: function(vals) {
        var thiscmd = this.part.attr("name");
        
        if ( thiscmd in vals ) {
            $("#"+this.jsid).selectpicker('val', vals[thiscmd]['bu-cvalue']);
            this.onChange();
            $.each(this.locontrols, function (idx, actrl) {
                actrl.setValue(vals[thiscmd]);
            })
        }
    },
    
    resetMe: function() {
    }
})
  


var sliderControl = Class.extend({
    init: function (ctxname, pname,part, realtime) {
        // Build a panel
        // Elt is the object on behalf of which we do this
        // Def is a parsed XML documents
        this.ctxname = ctxname;
        this.pname = pname;
        this.part = part;        
        this.jsid = this.ctxname.replace(/\s+/g, "_-_");
        if ( this.pname ) {
            this.jsid += "__"+this.pname.replace(/\s+/g, "_-_");
        }
        this.jsid += "__"+this.part.attr("name").replace(/\s+/g, "_-_");
        this.realtime = realtime || false;
        this.widget = undefined;
    },
    
    render: function (classes) {
        var tabmsg = "";
        if ( ! this.realtime || this.part.attr("rteffect")) {
            tabmsg += "<div id=\""+this.jsid+"_bucont\"";
            if (classes != undefined ) {
                tabmsg += " class=\""+classes+"\"";
            }
            tabmsg += ">";
            tabmsg += "<label class=\"bu-label\"  for=\""+this.jsid+"\">"+$(this.part).attr("label")+"</label>"
            tabmsg += "<input id=\""+this.jsid+ "\" type=\"text\" ";
            tabmsg += "data-slider-min=\""+(this.part.find("start").text() || "0") +"\" data-slider-max=\""+this.part.find("end").text() || "100";
            tabmsg += "\" data-slider-step=\""+(this.part.find("increment").text() || "1");
            var dval = this.part.find("default").text();

            if ( dval != undefined ) {
                tabmsg += "\" data-slider-value=\""+dval+"\" ";
            } else {
                    tabmsg += "\" data-slider-value=\""+(this.part.find("start").text() || "0")+"\" ";
            }
            tabmsg += " class=\"bu-slider-for-"+this.jsid+"\" /></div>"
            return tabmsg;
        } else {
            return "";
        }
    },   
    
    activate: function( size ) {
        
        this.widget = $("#"+this.jsid).bootstrapSlider({precision: 2});
        $("#"+this.jsid).data("buguiObj",this);    
             
    },
    
    setCallback: function( callback ) {
        if ( this.realtime &&  callback && this.part.attr("rteffect") ) {
            $("#"+this.jsid).on("slide",callback)
            $("#"+this.jsid).on("change",callback)
        }
    },
    
    getValue: function() {
        return this.widget.bootstrapSlider('getValue');
    },
    
    getDefault: function() {
        return this.part.find("default").text() || this.part.find("start").text() || "0"
    },
    
    setValue: function(vals) {
        if ( this.part.attr("name") in vals ) {
            this.widget.bootstrapSlider('setValue',vals[this.part.attr("name")])
        }
    },
    
    resetMe: function() {
    }
})

  
var switchControl = Class.extend({
    init: function (ctxname, pname,part, realtime) {
        // Build a panel
        // Elt is the object on behalf of which we do this
        // Def is a parsed XML documents
        this.ctxname = ctxname;
        this.pname = pname;
        this.part = part;        
        this.jsid = this.ctxname.replace(/\s+/g, "_-_");
        if ( this.pname ) {
            this.jsid += "__"+this.pname.replace(/\s+/g, "_-_");
        }
        this.jsid += "__"+this.part.attr("name").replace(/\s+/g, "_-_");
        this.realtime = realtime || false;
    },
    
    render: function (classes) { 
        var tabmsg = "";
        if ( ! this.realtime ||  this.part.attr("rteffect")) { 
            tabmsg += "<div  id=\""+this.jsid+"_bucont\"";
            if (classes != undefined ) {
                tabmsg += " class=\""+classes+"\"";
            }
            tabmsg += ">";
            tabmsg += "<label class=\"bu-label\" for=\""+this.jsid+"\">"+(this.part.attr("label") || this.part.attr("name"))+"</label>"
            tabmsg +="<input type=\"checkbox\" id=\""+this.jsid+"\" ";
            var self = this;
            var dval = this.part.find("default").text();
            var wascheck = false;
            $.each(this.part.children().filter("value"), function (idx, aval) {
                var  val=$(aval);
                if (idx == 0) {
                    tabmsg+=" data-on-text=\""+val.attr("label")+"\" "
                    tabmsg+=" bu-on-cmdvalue=\""+val.text()+"\" ";
                    if (dval == undefined && !wascheck) {
                        tabmsg +="checked ";
                        wascheck = true;
                    } else {
                        if ( dval == val.text() ) {
                            tabmsg +="checked ";
                            wascheck = true;
                        }
                    }
                } else {
                    tabmsg+=" data-off-text=\""+val.attr("label")+"\" "
                    tabmsg+=" bu-off-cmdvalue=\""+val.text()+"\" "
                }
            }) 
            
            tabmsg += " class=\"bu-switch-for-"+this.jsid+"\"  /></div>";
            return tabmsg;
        } else {
            return "";
        }
            
    },   
    
    activate: function( size ) {
        $("#"+this.jsid).bootstrapSwitch();
        $("#"+this.jsid).data("buguiObj",this);    
    },
    
    setCallback: function( callback ) {
        if ( this.realtime && this.part.attr("rteffect") ) {
            $("#"+this.jsid).on("switchChange.bootstrapSwitch",callback)
        }
    },
    
    getValue: function() {
        return ($("#"+this.jsid).bootstrapSwitch('state') && $("#"+this.jsid).attr("bu-on-cmdvalue")) || $("#"+this.jsid).attr("bu-off-cmdvalue");
    },
    
    setValue: function(vals) {
        if ( this.part.attr("name") in vals ) {
            $("#"+this.jsid).bootstrapSwitch('state',vals[this.part.attr("name")]==$("#"+this.jsid).attr("bu-on-cmdvalue"));
        }
    },
    
    resetMe: function() {
    }
})    
    
var spinnerControl = Class.extend({
    init: function (ctxname, pname,part, realtime) {
        // Build a panel
        // Elt is the object on behalf of which we do this
        // Def is a parsed XML documents
        this.ctxname = ctxname;
        this.pname = pname;
        this.part = part;        
        this.jsid = this.ctxname.replace(/\s+/g, "_-_");
        if ( this.pname ) {
            this.jsid += "__"+this.pname.replace(/\s+/g, "_-_");
        }
        this.jsid += "__"+this.part.attr("name").replace(/\s+/g, "_-_");
        this.realtime = realtime || false;
    },
    
    render: function (classes) {  
        var tabmsg = "";
        if ( ! this.realtime || this.part.attr("rteffect")) {
            tabmsg += "<span  id=\""+this.jsid+"_bucont\" ";
            if (classes != undefined ) {
                tabmsg += " class=\""+classes+"\"";
            }
            tabmsg += ">";
            tabmsg += "<label class=\"bu-label\" for=\""+this.jsid+"\">"+(this.part.attr("label") || this.part.attr("name"))+"</label>";
            tabmsg +="<input type=\"text\"  id=\""+this.jsid+"\" class=\"form-control text-center\"";
            var spvalue = this.part.find("default").text() || this.part.find("start").text();
            tabmsg += "\" value=\""+(spvalue || "0")+"\" ";
            tabmsg += " class=\"bu-spinner bu-spinner-for-"+this.jsid+"\"  /></span>";

            return tabmsg;
        } else {
            return "";
        }
    },   
    
    activate: function( size ) {
        var param = {};
        param["max"] = this.part.find("end").text() || 100;
        param["min"] = this.part.find("start").text() || 0;
        param["prefix"] = this.part.find("prefix").text() || "";
        param["postfix"] = this.part.find("postfix").text() || "";
        param["step"] = this.part.find("increment").text() || 1;
        param["decimals"] = this.part.find("decimals").text()|| 0;

        $("#"+this.jsid).TouchSpin(param);
        $("#"+this.jsid).data("buguiObj",this);    
             
    },
    
    setCallback: function( callback ) {
        if ( this.realtime &&  this.part.attr("rteffect") ) {
            $("#"+this.jsid).on("change",callback)
        }
    },
    
    getValue: function() {
        if (this.part.find("decimals").text() &&  parseInt(this.part.find("decimals").text()) != 0 ) {
            return parseFloat($("#"+this.jsid).val());
        } else {
            return parseInt($("#"+this.jsid).val());
        }
    },
    
    setValue: function(vals) {
        if ( this.part.attr("name") in vals ) {
            $("#"+this.jsid).val(vals[this.part.attr("name")])
        }
    },
    
    resetMe: function() {
    }
})    


var textControl = Class.extend({
    init: function (ctxname, pname,part, realtime) {
        // Build a panel
        // Elt is the object on behalf of which we do this
        // Def is a parsed XML documents
        this.ctxname = ctxname;
        this.pname = pname;
        this.part = part;        
        this.jsid = this.ctxname.replace(/\s+/g, "_-_");
        if ( this.pname ) {
            this.jsid += "__"+this.pname.replace(/\s+/g, "_-_");
        }
        this.jsid += "__"+this.part.attr("name").replace(/\s+/g, "_-_");
        this.realtime = realtime || false;
    },
    
    render: function (classes) {
        var tabmsg = "";
        if ( ! this.realtime ) {
            tabmsg += "<span  id=\""+this.jsid+"_bucont\"";
            if (classes != undefined ) {
                tabmsg += " class=\""+classes+"\"";
            }
            tabmsg += ">";
            tabmsg += "<label class=\"bu-label\" for=\""+this.jsid+"\">"+(this.part.attr("label") || (this.part.attr("name").charAt(0).toUpperCase()+this.part.attr("name").slice(1)))+"</label>";
            tabmsg +="<input type=\""
            if ( this.part.attr("itype") ) {
                tabmsg +=this.part.attr("itype")+"";
            } else {
                 tabmsg +="text";
            }
            tabmsg +="\" id=\""+this.jsid+"\" class=\"form-control\"";
            var spvalue = this.part.find("default").text();
            if ( this.part.attr("length") ) {
                tabmsg +=" maxlength=\""+this.part.attr("length")+"\""
            }
            tabmsg += " /></span>";

            return tabmsg;
        } else {
            return "";
        }
    },   
    
    activate: function( size ) {
        var spvalue = this.part.find("default").text();
        if ( spvalue ) {
            $("#"+this.jsid).val(spvalue);
        } else {
            $("#"+this.jsid).val("");
        } 
        $("#"+this.jsid).data("buguiObj",this);
    },
    
    setCallback: function( callback ) {
        if ( this.realtime && this.part.attr("rteffect") ) {
            $("#"+this.jsid).on("change",callback)
        }
    },
    
    getValue: function() {
        return $("#"+this.jsid).val();
    },
    
    setValue: function(vals) {
        if ( this.part.attr("name") in vals ) {
            $("#"+this.jsid).val(vals[this.part.attr("name")]);
        } else {
            $("#"+this.jsid).val("");
        }
    },
    
    resetMe: function() {
    }
})


var dateControl = Class.extend({
    init: function (ctxname, pname,part, realtime) {
        // Build a panel
        // Elt is the object on behalf of which we do this
        // Def is a parsed XML documents
        this.ctxname = ctxname;
        this.pname = pname;
        this.part = part;        
        this.jsid = this.ctxname.replace(/\s+/g, "_-_");
        if ( this.pname ) {
            this.jsid += "__"+this.pname.replace(/\s+/g, "_-_");
        }
        this.jsid += "__"+this.part.attr("name").replace(/\s+/g, "_-_");
        this.realtime = realtime || false;
    },
    
    render: function (classes) {
        var tabmsg = "";
        if ( ! this.realtime ) {
            tabmsg += "<div id=\""+this.jsid+"_bucont\"";
            if ( classes != undefined ) { 
                tabmsg += " class=\""+classes;
            }
            tabmsg += "\" >";
            if ( this.part.attr("label")  ) {
                tabmsg += "<label class=\"bu-label\" for=\""+this.jsid+"\">"+this.part.attr("label")+"</label>";
            }

            tabmsg += "<div id=\""+this.jsid+"\" ></div>";
            tabmsg += "</div>";
            return tabmsg;
        } else {
            return "";
        }
    },   
    
    activate: function( size ) {
        var param = {};
        $("#"+this.jsid).datepicker({
                changeMonth: true,
                changeYear: false,
                showButtonPanel: false,
            });
        $("#"+this.jsid).data("buguiObj",this);    
    },
    
    setCallback: function( callback ) {
        if ( this.realtime && this.part.attr("rteffect") ) {
            $("#"+this.jsid).on("input change",callback)
        }
    },
    
    getValue: function() {
        return ($("#"+this.jsid).datepicker("getDate").getMonth()+1).toString()+"/"+$("#"+this.jsid).datepicker("getDate").getDate().toString();
    },
    
    setValue: function(vals) {
        if ( this.part.attr("name") in vals ) {
            var zz = new Date(2017,parseInt(vals[this.part.attr("name")].split("/")[0])-1,parseInt(vals[this.part.attr("name")].split("/")[1]),0,0,0,0);
            $("#"+this.jsid).datepicker('setDate', zz);
        }
    },
    
    resetMe: function() {
    }
})



var timeControl = Class.extend({
    init: function (ctxname, pname,part, realtime) {
        // Build a panel
        // Elt is the object on behalf of which we do this
        // Def is a parsed XML documents
        this.ctxname = ctxname;
        this.pname = pname;
        this.part = part;        
        this.jsid = this.ctxname.replace(/\s+/g, "_-_");
        if ( this.pname ) {
            this.jsid += "__"+this.pname.replace(/\s+/g, "_-_");
        }
        this.jsid += "__"+this.part.attr("name").replace(/\s+/g, "_-_");
        this.realtime = realtime || false;
    },
    
    render: function (classes) {
        var tabmsg = "";
        if ( ! this.realtime ) {
            tabmsg += "<div id=\""+this.jsid+"_bucont\"";
            tabmsg +=" class=\"input-group ";
            if ( classes != undefined ) { 
                tabmsg +=classes;
            }
            tabmsg += "\" >";
            if ( this.part.attr("label")  ) {
                tabmsg += "<label class=\"bu-label\" for=\""+this.jsid+"\">"+this.part.attr("label")+"</label>";
            }
            tabmsg += "<span class=\"input-group bootstrap-timepicker timepicker\">"
            tabmsg += "<input id=\""+this.jsid+"\" type=\"text\" class=\"form-control input-small\">"
            tabmsg += "<span class=\"input-group-addon\"><i class=\"glyphicon glyphicon-time\"></i></span>"
            tabmsg += "</span>";
            return tabmsg;
        } else {
            return "";
        }
    },   
    
    activate: function( size ) {
        var param = {};       
        param["minuteStep"] = 1;
        param["showSeconds"] = false;
        param["showMeridian"] = false;
        param["decimal"] = 0;
        $("#"+this.jsid).timepicker(param); 
        $("#"+this.jsid).data("buguiObj",this);    
    },
    
    setCallback: function( callback ) {
        if ( this.realtime && this.part.attr("rteffect") ) {
            $("#"+this.jsid).on("changeTime.timepicker",callback)
        }
    },
    
    getValue: function() {
        return $("#"+this.jsid).val()
    },
    
    setValue: function(vals) {
        if ( this.part.attr("name") in vals ) {
            $("#"+this.jsid).timepicker('setTime', vals[this.part.attr("name")]);
        }
    },
    
    resetMe: function() {
    }
})

var timerangeControl = Class.extend({
    init: function (ctxname, pname,part, realtime) {
        // Build a panel
        // Elt is the object on behalf of which we do this
        // Def is a parsed XML documents
        this.ctxname = ctxname;
        this.pname = pname;
        this.part = part;        
        this.jsid = this.ctxname.replace(/\s+/g, "_-_");
        if ( this.pname ) {
            this.jsid += "__"+this.pname.replace(/\s+/g, "_-_");
        }
        this.jsid += "__"+this.part.attr("name").replace(/\s+/g, "_-_");
        this.realtime = realtime || false;
        this.callback = undefined;
    },
    
    render: function (classes) {
        var tabmsg = "";
        if ( ! this.realtime ) {
            tabmsg += "<div id=\""+this.jsid+"_bucont\"";
            tabmsg +=" class=\"input-group ";
            if ( classes != undefined ) { 
                tabmsg +=classes;
            }
            tabmsg += "\" >";
            if ( this.part.attr("label")  ) {
                tabmsg += "<label class=\"bu-label\" for=\""+this.jsid+"\">"+this.part.attr("label")+"</label>";
            }
            tabmsg += "<span class=\"input-group bootstrap-timepicker timepicker\">"
            tabmsg += "<input id=\""+this.jsid+"\" type=\"text\" class=\"form-control input-small\">"
            tabmsg += "<span class=\"input-group-addon\"><i class=\"glyphicon glyphicon-time\"></i></span>"
            tabmsg += "<span class=\"input-group-addon\"> and </span><input id=\""+this.jsid+"-after\" type=\"text\" class=\"form-control input-small\">"
            tabmsg += "<span class=\"input-group-addon\"><i class=\"glyphicon glyphicon-time\"></i></span>"
            tabmsg += "</span>";
            return tabmsg;
        } else {
            return "";
        }
    },   
    
    activate: function( size ) {
        var param = {};       
        param["minuteStep"] = 1;
        param["showSeconds"] = false;
        param["showMeridian"] = false;
        param["decimal"] = 0;
        $("#"+this.jsid).timepicker(param); 
        $("#"+this.jsid+"-after").timepicker(param); 
        $("#"+this.jsid).on("changeTime.timepicker", this.proxyChange);
        $("#"+this.jsid+"-after").on("changeTime.timepicker", this.proxyChange);
        $("#"+this.jsid).data("buguiObj",this);
        $("#"+this.jsid+"-after").data("buguiObj",this);
    },
    
    setCallback: function( callback ) {
        if ( this.realtime && this.part.attr("rteffect") ) {
            this.callback = callback;
        }
    },
    
    proxyChange: function(e) {
        if ( this.id.includes("-after") ){
            return $(this).data("buguiObj").onChangeAfter(e);
        } else {
            return $(this).data("buguiObj").onChange(e);
        }
    },
    
    onChange: function (e) {
        if (this.callback) {
            this.callback(e);
        }
        var cdate = new Date("January 1, 2017 " + $("#"+this.jsid+"-after")[0].value);
        var edate = new Date("January 1, 2017 " + e.time.value);
        if (cdate.getTime() < edate.getTime()) {
            $("#"+this.jsid+"-after").timepicker('setTime', e.time.value);
        }
    },
    
    onChangeAfter: function (e) {
        if (this.callback) {
            this.callback(e);
        }
        var cdate = new Date("January 1, 2017 " + $("#"+this.jsid)[0].value);
        var edate = new Date("January 1, 2017 " + e.time.value);
        if (cdate.getTime() > edate.getTime()) {
            $("#"+this.jsid).timepicker('setTime', e.time.value);
        }
    },
    
    getValue: function() {
        return  [$("#"+this.jsid).val(),$("#"+this.jsid+"-after").val()];
    },
    
    setValue: function(vals) {
        if ( this.part.attr("name") in vals ) {
            $("#"+this.jsid).timepicker('setTime', vals[this.part.attr("name")][0]);
            $("#"+this.jsid+"-after").timepicker('setTime', vals[this.part.attr("name")][1]);
        }
    },
    
    resetMe: function() {
    }
})


$("head").append('<style type="text/css"></style>');
var newStyleElement = $("head").children(':last');
newStyleElement.html('.ui-datepicker-year{display:none;}');