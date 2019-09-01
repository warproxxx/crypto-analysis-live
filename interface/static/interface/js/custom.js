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
