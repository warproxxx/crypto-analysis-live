$(document).ready(function(){
    $('.table td.colored').each(function(){
        var txt = $(this).text();
        txt = txt.replace(' %', '');
        txt = txt.replace('%', '');

        

        if (txt < 0) {
            $(this).css('background-color','#FF0000');
            $(this).css('color','white');
        }
        else if (txt > 0){
            $(this).css('background-color','#008000');
            $(this).css('color','white');
        }
    });
});

$(document).ready(function(){
    $('.table tr.colored').each(function(){
        $td = $(this).find("td:nth-child(4)"); 
        var txt = $td.text();

        if (txt.includes("SHORT")) {
            $(this).css('background-color','#FF0000');
            $(this).css('color','white');
        }
        else if (txt.includes("LONG")){
            $(this).css('background-color','#008000');
            $(this).css('color','white');
        }
        
    });
});

$(document).ready(function(){
    $('.table td.colored_text').each(function(){
        var txt = $(this).text();
        

        if (txt.includes("SHORT") || txt.includes("CLOSE")) {
            $(this).css('background-color','#FF0000');
            $(this).css('color','white');
        }
        else if (txt.includes("LONG") || txt.includes("OPEN")){
            $(this).css('background-color','#008000');
            $(this).css('color','white');
        }
        else if (txt.includes("HODL")){
            $(this).css('background-color','black');
            $(this).css('color','white');
        }
    });
});

$(document).ready(function(){
    $('h2.colored_header').each(function(){
        var txt = $(this).text();
        txt = txt.replace('MACD: ', '');
        txt = txt.replace('Change: ', '');
        txt = txt.replace('%', '');

        if (txt < 0) {
            $(this).css('background-color','#FF0000');
            $(this).css('color','white');
        }
        else if (txt > 0){
            $(this).css('background-color','#008000');
            $(this).css('color','white');
        }
    });
});

