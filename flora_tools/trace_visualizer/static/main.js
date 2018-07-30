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
                let $hint = $('#visualization.visualization > .file_hint');
                $hint.hide();
                new Timeline('#visualization .timeline', trace, renderStat);
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
                let $hint = $('#visualization.visualization .file_hint');
                $hint.hide();
                new Timeline('#visualization .timeline', trace, renderStat);
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


function renderStat(selection) {
    let $stats = $('.stats');
    $stats.empty();

    if (selection.start !== null && selection.stop !== null && selection.activities.length) {


        for (let i = 0; i < selection.nodeCount; i++) {

            $stats.removeClass('no_selection');

            let nodeActivities = selection.activities.filter(element => {
                return (element.node === i);
            });

            let txEnergy = nodeActivities.reduce((accumulator, element) => {
                if (element.energy !== null && element.activity_type === 'TxActivity') {
                    return accumulator + element.energy;
                }
                else {
                    return accumulator;
                }
            }, 0);

            let rxEnergy = nodeActivities.reduce((accumulator, element) => {
                if (element.energy !== null && ['RxActivity', 'CADActivity'].includes((element.activity_type))) {
                    return accumulator + element.energy;
                }
                else {
                    return accumulator;
                }
            }, 0);

            if (txEnergy || rxEnergy) {

                let data = {
                    datasets: [{
                        data: [txEnergy, rxEnergy],
                        backgroundColor: ['crimson', 'cornflowerblue']
                    }],
                    labels: ['Tx', 'Rx']
                };

                let $nodeStat = $('<div>').attr({class: 'node_stat'}).css({height: $('.visualization .timeline').height() / selection.nodeCount});
                $stats.append($nodeStat);

                let $chartContainer = $('<div>').attr({class: 'chart_container'});
                $nodeStat.append($chartContainer);


                let $canvas = $('<canvas>').attr({width: $chartContainer.width(), height: $chartContainer.height()});
                $chartContainer.append($canvas);

                let ctx = $canvas.get(0).getContext('2d');

                let pieChart = new Chart(ctx, {
                    type: 'doughnut',
                    data: data,
                    options: {
                        legend: {
                            display: false
                        },
                    }
                });

                let $statDetails = $('<div>').attr({class: 'stat_details'});
                $statDetails.html($(`<h3>${i.toString()} (${(txEnergy + rxEnergy).toPrecision(2)} mJ)</h3><p><span class="badge badge-danger">Tx</span>: ${txEnergy.toPrecision(6)} mJ<br /><span class="badge badge-info">Rx</span>: ${rxEnergy.toPrecision(6)} mJ</p>`));
                $nodeStat.append($statDetails)


            }
            else {
                let $nodeStat = $('<div>').attr({class: 'node_stat'}).css({height: $('.visualization .timeline').height() / selection.nodeCount});
                $nodeStat.text("(No energy)");
                $stats.append($nodeStat);
            }
        }
    }
    else {
        $stats.addClass('no_selection');
        $stats.append($('<p>No selection<p>'));
    }

}