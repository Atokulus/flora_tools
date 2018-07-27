slot_colors = {
    SYNC: 'fuchsia',
    ROUND_SCHEDULE: 'rebeccapurple',
    CONTENTION: 'lightcoral',
    SLOT_SCHEDULE: 'darkorchid',
    DATA: 'deepskyblue',
    ACK: 'mediumaquamarine',
};

$(function () {
    if (window.File && window.FileReader && window.FileList && window.Blob) {
        // Great success!

        function handleJSONDrop(evt) {
            evt.stopPropagation();
            evt.preventDefault();
            var files = evt.dataTransfer.files;
            // Loop through the FileList and read
            for (var i = 0, f; f = files[i]; i++) {

                // Only process json files.
                if (!f.type.match('application/json')) {
                    console.log("Not a JSON file!");
                    continue;
                }

                var reader = new FileReader();

                // Closure to capture the file information.
                reader.onload = (function (theFile) {
                    return function (e) {
                        let p = JSON.parse(e.target.result);

                        $('#container').hide();
                        $('#svg').empty();

                        let s = Snap("#svg");
                        draw_trace(s, p);
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

        // Setup the dnd listeners.
        var dropZone = document.getElementsByTagName('body')[0];
        dropZone.addEventListener('dragover', handleDragOver, false);
        dropZone.addEventListener('drop', handleJSONDrop, false);


    } else {
        alert('The File APIs are not fully supported in this browser.');
    }
});


function draw_trace(s, trace) {
    scale = 250;
    console.log(trace);

    let nodeCount = trace.network.nodes.length;
    console.log(`nodeCount is ${nodeCount}`);

    let modulations = trace.network.modulations;

    modulationsColors = modulations.map(modulation => {
        return `rgba(${modulation.color[0] * 255}, ${modulation.color[1] * 255}, ${modulation.color[2] * 255}, ${modulation.color[3]})`
    });
    console.log(modulationsColors);


    function draw_activity(activity) {
        node_offset = activity.node;

        if (activity.activity_type === "LWBRoundActivity") {
            s.rect(activity.start * scale, node_offset * scale, (activity.end - activity.start) * scale, 0.8 * scale).attr({
                fill: 'transparent',
                style: `stroke: ${modulationsColors[activity.details.modulation]};`
            });

            s.text((activity.end + activity.start) / 2 * scale, (node_offset + 0.2) * scale, activity.details.round_type).attr({
                'font-size': Math.min((activity.end - activity.start) / 10 * scale, 0.1 * scale),
                'text-anchor': 'middle'
            });
        }

        else if (activity.activity_type === "LWBSlotActivity") {
            s.rect(activity.start * scale, (node_offset + 0.3) * scale, (activity.end - activity.start) * scale, 0.5 * scale).attr({
                fill: slot_colors[activity.details.slot_type]
            });
        }

        else if (activity.activity_type === "CADActivity") {
            s.rect(activity.start * scale, (node_offset + 0.5) * scale, (activity.end - activity.start) * scale, 0.3 * scale).attr({
                fill: 'blue'
            });
        }

        else if (activity.activity_type === "RxActivity") {
            s.rect(activity.start * scale, (node_offset + 0.5) * scale, (activity.end - activity.start) * scale, 0.3 * scale).attr({
                fill: 'cyan'
            });
        }

        else if (activity.activity_type === "TxActivity") {
            s.rect(activity.start * scale, (node_offset + 0.5) * scale, (activity.end - activity.start) * scale, 0.3 * scale).attr({
                fill: 'crimson'
            });
        }
    }

    trace.activities.forEach(draw_activity)


}



