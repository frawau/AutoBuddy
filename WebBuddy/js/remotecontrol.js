/*
* Remote control widget
* Copyright (c) 2017 François Wautier
* Licensed under the MIT (http://www.opensource.org/licenses/mit-license.php) license.
*/

remotecontrol = function(target, size, prefix){
    var buttons={"up":false, "down":false, "left":false, "right":false, "enter":false,
                 "back":false, "home":false, "play":false, "previous":false, "next":false,
                 "forward":false, "backward":false, "isplaying": false}, // isplaying...true: displaying pause foreground, false; displaying play foregrounf 
        bu_callback,
        bu_gencallback,
        idprefix = prefix || "bu-";


    function create ( target, size) {
        
        var newElement, onewElement;
        var svgElement = document.createElementNS("http://www.w3.org/2000/svg", 'svg'); //Create a path in SVG's namespace
        svgElement.setAttribute("id",idprefix+"remotecontrol");
        svgElement.setAttribute("viewBox","0 0 1100 1600");
        svgElement.setAttribute("width", size);
        svgElement.setAttribute("height", (size*1100)/1600);
        var defsElement = document.createElementNS("http://www.w3.org/2000/svg", 'defs');
        defsElement.setAttribute("id",idprefix+"remotecontrol-defs");
        
        newElement = document.createElementNS("http://www.w3.org/2000/svg", 'path');
        newElement.setAttribute("id",idprefix+"dir-button");
        var mypath = `M175 50 L 475 50 L 537.5 0 L 600 50  L 925 50 A 100 100, 0, 0, 1, 995.7 79.3 
                      L 925 150 A 800 900, 0, 0, 1, 175 150 L 104.3 79.3 A 100 100, 0, 0, 1, 175 50`;
        newElement.setAttribute("d",mypath);
        defsElement.appendChild(newElement);
        svgElement.appendChild(defsElement);

        //Up button
        newElement = document.createElementNS("http://www.w3.org/2000/svg", 'use');
        newElement.setAttribute("id",idprefix+"up-button");
        newElement.setAttribute("class","bu-remote-button");
        newElement.setAttributeNS('http://www.w3.org/1999/xlink','href',"#"+idprefix+"dir-button");
        svgElement.appendChild(newElement);
        newElement.addEventListener("click", up_click);
        //Right button
        newElement = document.createElementNS("http://www.w3.org/2000/svg", 'use');
        newElement.setAttribute("id",idprefix+"right-button");
        newElement.setAttribute("class","bu-remote-button");
        newElement.setAttributeNS('http://www.w3.org/1999/xlink','href',"#"+idprefix+"dir-button");
        newElement.setAttribute("transform","rotate(90, 550, 550)");
        svgElement.appendChild(newElement);
        newElement.addEventListener("click", right_click);
        //Down button
        newElement = document.createElementNS("http://www.w3.org/2000/svg", 'use');
        newElement.setAttribute("id",idprefix+"down-button");
        newElement.setAttribute("class","bu-remote-button");
        newElement.setAttributeNS('http://www.w3.org/1999/xlink','href',"#"+idprefix+"dir-button");
        newElement.setAttribute("transform","rotate(180, 550, 550)");
        svgElement.appendChild(newElement);
        newElement.addEventListener("click", down_click);
        //Left button
        newElement = document.createElementNS("http://www.w3.org/2000/svg", 'use');
        newElement.setAttribute("id",idprefix+"left-button");
        newElement.setAttribute("class","bu-remote-button");
        newElement.setAttributeNS('http://www.w3.org/1999/xlink','href',"#"+idprefix+"dir-button");
        newElement.setAttribute("transform","rotate(-90, 550, 550)");
        svgElement.appendChild(newElement);
        newElement.addEventListener("click", left_click);
        
        //Enter button
        newElement = document.createElementNS("http://www.w3.org/2000/svg", 'circle');
        newElement.setAttribute("id",idprefix+"enter-button");
        newElement.setAttribute("class","bu-remote-button");
        newElement.setAttribute("cx",550);
        newElement.setAttribute("cy",559);
        newElement.setAttribute("r",200);
        svgElement.appendChild(newElement);
        newElement.addEventListener("click", enter_click);
        
        //Back button
        newElement = document.createElementNS("http://www.w3.org/2000/svg", 'g');
        newElement.setAttribute("id",idprefix+"back-button");
        
        onewElement = document.createElementNS("http://www.w3.org/2000/svg", 'rect');
        onewElement.setAttribute("id",idprefix+"back-button-bg");
        onewElement.setAttribute("class","bu-remote-button-bg");
        onewElement.setAttribute("x",160);
        onewElement.setAttribute("y",1155);
        onewElement.setAttribute("rx",20);
        onewElement.setAttribute("ry",20);
        onewElement.setAttribute("width",250);
        onewElement.setAttribute("height",190);
        newElement.appendChild(onewElement);
        
        onewElement = document.createElementNS("http://www.w3.org/2000/svg", 'path');
        onewElement.setAttribute("id",idprefix+"back-button-fg");
        onewElement.setAttribute("class","bu-remote-button-fg");
        mypath = `M197.5 1280 l0 30 l150 0 a55 55, 0, 1, 0, 0 -110 l-150 0 l0 -15 l -30 30 l 30 30 
                  l0 -15 l150 0 a25 25, 0, 0, 1, 0 50`;
        onewElement.setAttribute("d",mypath);
        newElement.appendChild(onewElement);
        svgElement.appendChild(newElement);
        newElement.addEventListener("click", back_click);
        
        //Home button
        newElement = document.createElementNS("http://www.w3.org/2000/svg", 'g');
        newElement.setAttribute("id",idprefix+"home-button");
        
        onewElement = document.createElementNS("http://www.w3.org/2000/svg", 'rect');
        onewElement.setAttribute("id",idprefix+"home-button-bg");
        onewElement.setAttribute("class","bu-remote-button-bg");
        onewElement.setAttribute("x",640);
        onewElement.setAttribute("y",1155);
        onewElement.setAttribute("rx",20);
        onewElement.setAttribute("ry",20);
        onewElement.setAttribute("width",250);
        onewElement.setAttribute("height",190);
        newElement.appendChild(onewElement);
        
        onewElement = document.createElementNS("http://www.w3.org/2000/svg", 'path');
        onewElement.setAttribute("id",idprefix+"home-button-fg");
        onewElement.setAttribute("class","bu-remote-button-fg");
        mypath = `M650 1332.5 l90 0 l0 -40 l20 0 l0 40 l90 0 l0 -105 l20 0 l-22 -11.82 l0 -25 l-20 0
                  l0 14.17 l-78 -42.25 l-85 65 l20 0 l0 105`;
        onewElement.setAttribute("d",mypath);
        newElement.appendChild(onewElement);
        svgElement.appendChild(newElement);
        newElement.addEventListener("click", home_click);
        
        //Previous button
        newElement = document.createElementNS("http://www.w3.org/2000/svg", 'g');
        newElement.setAttribute("id",idprefix+"previous-button");
        
        onewElement = document.createElementNS("http://www.w3.org/2000/svg", 'rect');
        onewElement.setAttribute("id",idprefix+"previous-button-bg");
        onewElement.setAttribute("class","bu-remote-button-bg");
        onewElement.setAttribute("x",55);
        onewElement.setAttribute("y",1405);
        onewElement.setAttribute("rx",20);
        onewElement.setAttribute("ry",20);
        onewElement.setAttribute("width",190);
        onewElement.setAttribute("height",190);
        newElement.appendChild(onewElement);
        
        onewElement = document.createElementNS("http://www.w3.org/2000/svg", 'path');
        onewElement.setAttribute("id",idprefix+"previous-button-fg");
        onewElement.setAttribute("class","bu-remote-button-fg");
        mypath = `M120 1440 l0 120 l5 0 l0 -60 l60 60 l0 -120 l-60 60 l0 -60`;
        onewElement.setAttribute("d",mypath);
        newElement.appendChild(onewElement);
        svgElement.appendChild(newElement);
        newElement.addEventListener("click", previous_click);
        
        //Backward button
        newElement = document.createElementNS("http://www.w3.org/2000/svg", 'g');
        newElement.setAttribute("id",idprefix+"backward-button");
        
        onewElement = document.createElementNS("http://www.w3.org/2000/svg", 'rect');
        onewElement.setAttribute("id",idprefix+"backward-button-bg");
        onewElement.setAttribute("class","bu-remote-button-bg");
        onewElement.setAttribute("x",255);
        onewElement.setAttribute("y",1405);
        onewElement.setAttribute("rx",20);
        onewElement.setAttribute("ry",20);
        onewElement.setAttribute("width",190);
        onewElement.setAttribute("height",190);
        newElement.appendChild(onewElement);
        
        onewElement = document.createElementNS("http://www.w3.org/2000/svg", 'path');
        onewElement.setAttribute("id",idprefix+"backward-button-fg");
        onewElement.setAttribute("class","bu-remote-button-fg");
        mypath = `M280 1500 l60 60 l0 -60 l60 60 l0 -120 l-60 60 l0 -60`;
        onewElement.setAttribute("d",mypath);
        newElement.appendChild(onewElement);
        svgElement.appendChild(newElement);
        newElement.addEventListener("click", backward_click);
        
        //Play button
        newElement = document.createElementNS("http://www.w3.org/2000/svg", 'g');
        newElement.setAttribute("id",idprefix+"play-button");
        
        onewElement = document.createElementNS("http://www.w3.org/2000/svg", 'rect');
        onewElement.setAttribute("id",idprefix+"play-button-bg");
        onewElement.setAttribute("class","bu-remote-button-bg");
        onewElement.setAttribute("x",455);
        onewElement.setAttribute("y",1405);
        onewElement.setAttribute("rx",20);
        onewElement.setAttribute("ry",20);
        onewElement.setAttribute("width",190);
        onewElement.setAttribute("height",190);
        newElement.appendChild(onewElement);
        
        onewElement = document.createElementNS("http://www.w3.org/2000/svg", 'path');
        onewElement.setAttribute("id",idprefix+"play-button-fg");
        onewElement.setAttribute("class","bu-remote-button-fg");
        mypath = `M500 1440 l0 120 l120 -60 l-120 -60`;
        onewElement.setAttribute("d",mypath);
        newElement.appendChild(onewElement);
        
        onewElement = document.createElementNS("http://www.w3.org/2000/svg", 'path');
        onewElement.setAttribute("id",idprefix+"play-button-fg-alt");
        onewElement.setAttribute("class","bu-remote-button-fg bu-remote-button-fg-hidden");
        mypath = `M510 1440 l0 120 l30 0 l0 -120 l-30 0 m50 0 l0 120 l30 0 l0 -120 l-30 0`;
        onewElement.setAttribute("d",mypath);
        newElement.appendChild(onewElement);
        svgElement.appendChild(newElement);
        newElement.addEventListener("click", play_click);
        
        //Forward button
        newElement = document.createElementNS("http://www.w3.org/2000/svg", 'g');
        newElement.setAttribute("id",idprefix+"forward-button");
        
        onewElement = document.createElementNS("http://www.w3.org/2000/svg", 'rect');
        onewElement.setAttribute("id",idprefix+"forward-button-bg");
        onewElement.setAttribute("class","bu-remote-button-bg");
        onewElement.setAttribute("x",655);
        onewElement.setAttribute("y",1405);
        onewElement.setAttribute("rx",20);
        onewElement.setAttribute("ry",20);
        onewElement.setAttribute("width",190);
        onewElement.setAttribute("height",190);
        newElement.appendChild(onewElement);
        
        onewElement = document.createElementNS("http://www.w3.org/2000/svg", 'path');
        onewElement.setAttribute("id",idprefix+"forward-button-fg");
        onewElement.setAttribute("class","bu-remote-button-fg");
        mypath = `M820 1500 l-60 60 l0 -60 l-60 60 l0 -120 l60 60 l0 -60`;
        onewElement.setAttribute("d",mypath);
        newElement.appendChild(onewElement);
        svgElement.appendChild(newElement);
        newElement.addEventListener("click", forward_click);
        
        //Next button
        newElement = document.createElementNS("http://www.w3.org/2000/svg", 'g');
        newElement.setAttribute("id",idprefix+"next-button");
        
        onewElement = document.createElementNS("http://www.w3.org/2000/svg", 'rect');
        onewElement.setAttribute("id",idprefix+"next-button-bg");
        onewElement.setAttribute("class","bu-remote-button-bg");
        onewElement.setAttribute("x",855);
        onewElement.setAttribute("y",1405);
        onewElement.setAttribute("rx",20);
        onewElement.setAttribute("ry",20);
        onewElement.setAttribute("width",190);
        onewElement.setAttribute("height",190);
        newElement.appendChild(onewElement);
        
        onewElement = document.createElementNS("http://www.w3.org/2000/svg", 'path');
        onewElement.setAttribute("id",idprefix+"next-button-fg");
        onewElement.setAttribute("class","bu-remote-button-fg");
        mypath = `M980 1440 l0 120 l-5 0 l0 -60 l-60 60 l0 -120 l60 60 l0 -60`;
        onewElement.setAttribute("d",mypath);
        newElement.appendChild(onewElement);
        svgElement.appendChild(newElement);
        newElement.addEventListener("click", next_click);
        
        
        target.appendChild(svgElement);
        return signature()
    };
    
    //Utility functions
    function reset_button(butname) {
        buttons[butname] = false;
        if ( ['up','down','left','right','enter'].includes(butname) ) {
            var myelt =  document.getElementById(idprefix+butname+"-button");
            myelt.setAttribute("class","bu-remote-button");
            return;
        }
        
        var myelt =  document.getElementById(idprefix+butname+"-button-bg");
        myelt.setAttribute("class","bu-remote-button-bg");
        if ( butname == "play" ) {
            //handle foreground
            if ( buttons["isplaying"] ) {
                myelt =  document.getElementById(idprefix+butname+"-button-fg");
                myelt.setAttribute("class","bu-remote-button-fg bu-remote-button-fg-hidden");
                myelt =  document.getElementById(idprefix+butname+"-button-fg-alt");
                myelt.setAttribute("class","bu-remote-button-fg");
            } else {
                myelt =  document.getElementById(idprefix+butname+"-button-fg-alt");
                myelt.setAttribute("class","bu-remote-button-fg bu-remote-button-fg-hidden");
                myelt =  document.getElementById(idprefix+butname+"-button-fg");
                myelt.setAttribute("class","bu-remote-button-fg");
            }
        }
        return;
    
    };
    
    function toggle_button(butname,e) {
        
        if ( ['up','down','left','right','enter'].includes(butname) ) {
            var myelt =  document.getElementById(idprefix+butname+"-button");
        } else {
            var myelt =  document.getElementById(idprefix+butname+"-button-bg");
        }
        
        myelt.setAttribute("class","bu-remote-button-highlight");
        buttons[butname] = true;
        
        if ( bu_gencallback ) { //We are live!
            bu_gencallback(e)
            buttons[butname] = false;
            setTimeout(reset_button,100,butname);
        } else if ( bu_callback ) { //We are live!
            bu_callback(buttons)
            buttons[butname] = false;
            setTimeout(reset_button,100,butname);
        }
        
    };
    
        
    function process_button(bname,e) {
        //Revert any other button set
        Object.keys(buttons).forEach(function(key, index) {
            if (key != "isplaying") {
                if ( buttons[key] == true ) {
                    if ( key != bname ) {
                        reset_button(key);
                    }
                }
            }
        });
        toggle_button(bname,e)
    }; 
    
    //Event handlers
    function up_click(e) {
        process_button("up",e);
        return false;
    };
    function right_click(e) {
        process_button("right",e);
        return false;
    };
    function down_click(e) {
        process_button("down",e);
        return false;
    };
    function left_click(e) {
        process_button("left",e);
        return false;
    };
    function back_click(e) {
        process_button("back",e);
        return false;
    };
    function home_click(e) {
        process_button("home",e);
        return false;
    };
    function previous_click(e) {
        process_button("previous",e);
        return false;
    };
    function backward_click(e) {
        process_button("backward",e);
        return false;
    };
    function play_click(e) {
        if ( bu_gencallback ) {
            buttons["isplaying"] = ! buttons["isplaying"];
        }
        process_button("play",e);
        return false;
    };
    function forward_click(e) {
        process_button("forward",e);
        return false;
    };
    function next_click(e) {
        process_button("next",e);
        return false;
    };
    function enter_click(e) {
        process_button("enter",e);
        return false;
    };
    
    //Signature functions
    function onchange(fcnt) {
        bu_callback=fcnt;
        reset_button("play");
    };
    
    //Signature functions
    function onChange(fcnt) {
        bu_gencallback=fcnt;
        reset_button("play");
    };
    
    function setValue(V) {
        Object.keys(V).forEach(function(key, index) {
            if ( key in buttons ) {
                buttons[key] = V[key];
            }
        })
        if ( "isplaying" in V ) {
            if ( bu_gencallback ) {
                reset_button("play");
            }
        } else {
            buttons["isplaying"]=false;
        }
            
    };
    
    function getValue() {
        var resu = {};
        Object.keys(buttons).forEach(function(key, index) {
            resu[key] = buttons[key];
        });
        return resu;
    };

    // The object returned
    function signature(){
        return {
            val: getValue,
            setValue: setValue,
            getValue: getValue,
            onChange: onChange,
            onchange: onchange,
        };
    }
    
    return create(target,size);
}

// Integration with buddyguilib. Providing "remotecontrol" widget
if ( typeof buwidgetRegistry !== 'undefined' ) {
    var buwrprefix=1;
    buwidgetRegistry["remotecontrol"]= function( target , hsize, vsize ) {
        buwrprefix+=1;
        return remotecontrol( target, hsize, "burc"+buwrprefix+"-")
    }
}
