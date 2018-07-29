import {Timeline} from './timeline.js'

$(function () {
    if (window.File && window.FileReader && window.FileList && window.Blob) {
        // Great success!

        // Setup the dnd listeners.
        let dropZone = $('body').get(0);
        dropZone.addEventListener('dragover', handleDragOver, false);
        dropZone.addEventListener('drop', handleJSONDrop, false);

        $('input[type="file"]').change(handleFileSelect);


    } else {
        alert('The File APIs are not fully supported in this browser.');
    }
});

function handleFileSelect(evt) {
    var files = evt.target.files; // FileList object

    for (let i = 0, f; f = files[i]; i++) {

        // Only process json files.
        if (!f.type.match('application/json')) {
            console.log("Not a JSON file!");
            continue;
        }

        let reader = new FileReader();

        // Closure to capture the file information.
        reader.onload = (function (theFile) {
            return function (e) {
                let trace = JSON.parse(e.target.result);
                let svg = $().get();
                let $hint = $('#visualization.visualization .dragndrop_hint');
                $hint.hide();
                new Timeline('#visualization .timeline', trace);
            };
        })(f);

        reader.readAsText(f);
    }
}


function handleJSONDrop(evt) {
    evt.stopPropagation();
    evt.preventDefault();
    let files = evt.dataTransfer.files;
    // Loop through the FileList and read
    for (let i = 0, f; f = files[i]; i++) {

        // Only process json files.
        if (!f.type.match('application/json')) {
            console.log("Not a JSON file!");
            continue;
        }

        let reader = new FileReader();

        // Closure to capture the file information.
        reader.onload = (function (theFile) {
            return function (e) {
                let trace = JSON.parse(e.target.result);
                let svg = $().get();
                let $hint = $('#visualization.visualization .dragndrop_hint');
                $hint.hide();
                new Timeline('#visualization .timeline', trace);
            };
        })(f);

        reader.readAsText(f);
    }
}

function handleDragOver(evt) {
    evt.stopPropagation();
    evt.preventDefault();
    evt.dataTransfer.dropEffect = 'copy'; // Explicitly show this is a copy.
}



