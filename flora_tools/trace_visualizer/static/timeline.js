const slot_colors = {
    SYNC: 'fuchsia',
    ROUND_SCHEDULE: 'rebeccapurple',
    CONTENTION: 'lightcoral',
    SLOT_SCHEDULE: 'darkorchid',
    DATA: 'deepskyblue',
    ACK: 'mediumaquamarine',
};

export class Timeline {
    constructor(svg, trace, selectionCallback) {
        this.selectionCallback = selectionCallback;
        this.svg = svg;
        this.$svg = $(svg);

        this.trace = trace;
        this.sortTraceByStart();
        console.log(this.trace);

        this.s = Snap(svg);

        this.modulations = this.trace.network.modulations;
        this.modulationsColors = this.modulations.map(modulation => {
            return `rgba(${modulation.color[0] * 255}, ${modulation.color[1] * 255}, ${modulation.color[2] * 255}, ${modulation.color[3]})`
        });

        this.selection = {start: null, stop: null};
        this.nodeCount = this.trace.network.nodes.length;

        this.initActivities();
        this.drawActivities();

        this.sortTraceByEnd();

        this.initSelection();
        this.initNodeMarker();
        this.initDescriptors();

        this.initMarkers();
        this.initBoundaries();

        this.initMouseMarker();

        this.register_mouse_interaction();
    }

    register_mouse_interaction() {
        let isPanning = false;
        let isSelecting = false;
        let lastMousePosition = null;

        this.$svg.mousemove(event => {
            let x = event.pageX - this.$svg.offset().left;
            let y = event.pageY - this.$svg.offset().top;

            if (isPanning && lastMousePosition !== null) {
                let dx = x - lastMousePosition.x;
                let dy = y - lastMousePosition.y;
                let svg_width = this.$svg.width();
                this.position -= (dx / svg_width) * this.zoom;
                this.updateViewbox();
            }

            if (isSelecting) {
                this.selection.stop = this.calculateTimeCoordinate(event.pageX - this.$svg.offset().left);
                this.updateViewbox();
            }

            this.updateMouseMarker(x);

            lastMousePosition = {x: x, y: y};
            event.stopPropagation();
        });

        this.$svg.mousedown(event => {
            if (event.which === 3) {
                this.selection.start = this.calculateTimeCoordinate(event.pageX - this.$svg.offset().left);
                isSelecting = true;

                event.preventDefault();
                event.stopPropagation();
            }
            else {
                isPanning = true;
            }
        });

        this.$svg.mouseup(event => {
            if (event.which === 3) {
                this.selection.stop = this.calculateTimeCoordinate(event.pageX - this.$svg.offset().left);
                isSelecting = false;

                if (this.selection.start === this.selection.stop) {
                    this.selection.x = null;
                    this.selection.y = null;
                }

                this.updateViewbox();
                this.getActivitiesInSelection();
            }
            else {
                isPanning = false;
            }
        });

        this.$svg.mouseleave(event => {
            isPanning = false;

            this.updateMouseMarker(-100);
        });

        this.$svg.on('mousewheel', event => {
            let dZoom = Math.exp(-event.originalEvent.wheelDelta / 240);
            let fixedX = (event.pageX - this.$svg.offset().left) / this.$svg.width();
            let fixedPosition = this.position - (0.5 - fixedX) * this.zoom;

            if (this.zoom > 0.001 || dZoom >= 1) {
                this.position = fixedPosition + this.zoom * dZoom * (0.5 - fixedX);
                this.zoom *= dZoom;
            }

            this.updateViewbox();
            event.stopPropagation();
        });

        this.$svg.on('contextmenu', event => {
            event.preventDefault();
            event.stopPropagation();
        });

        $('body').resize(event => {
            this.updateViewbox();
        });

        $(document).keydown(event => {
            if (event.which === 36) { // Home Key
                this.initBoundaries();
            }
        })
    }

    initBoundaries() {
        this.s.attr({'preserveAspectRatio': 'none'});

        this.begin = this.trace.activities[0].start;
        this.end = this.trace.activities[this.trace.activities.length - 1].end;

        this.position = (this.begin + this.end) / 2;
        this.zoom = (this.end - this.begin) * 1.1;

        this.updateViewbox();
    }


    updateViewbox() {
        let x = this.position - this.zoom / 2;
        let y = 0;

        let wi = this.zoom;
        let hi = this.nodeCount;

        let svg_width = this.$svg.width();
        let svg_height = this.$svg.height();

        let matrix = new Snap.Matrix();

        matrix.translate(svg_width / 2 - this.position, 0);
        matrix.scale(svg_width / this.zoom, svg_height / this.nodeCount, this.position, 0);

        this.activities.transform(matrix);

        this.updateMarkers();
        this.updateSelectionRect();
        this.updateNodeMarker();
        this.updateDescriptors();
    }

    initActivities() {
        this.activities = this.s.group().attr({class: 'activities'});
        this.s.append(this.activities);
    }

    initMarkers() {
        this.markers = [];
        this.gMarkers = this.s.group().attr({class: 'markers'});
        this.s.append(this.gMarkers);

        this.markerCount = 110;

        for (let i = 0; i < this.markerCount; i++) {
            let marker = this.s.group();
            let line = this.s.line(0, 0, 0, -10).attr({stroke: 'white'});

            if (!(i % 10)) {
                line.attr({strokeWidth: 2});
                let text = this.s.text(0, 20, "").attr({fill: 'white', textAnchor: 'middle'});
                marker.append(text);
            }


            marker.append(line);


            this.markers.push(marker);
            this.gMarkers.add(marker);
        }
    }

    updateMarkers() {
        let magnitude = Math.floor(Math.log10(this.zoom));

        let bigStep = Math.pow(10, magnitude);
        let step = Math.pow(10, magnitude - 1);
        let offset = Math.floor((this.position - this.zoom / 2) / bigStep) * bigStep;

        for (let i = 0; i < this.markerCount; i++) {
            let pos = this.calculateDisplayCoordinate(offset, this.nodeCount);

            let matrix = new Snap.Matrix();
            matrix.translate(pos.x, pos.y);

            this.markers[i].transform(matrix);

            if (!(i % 10)) {
                this.markers[i].select('text').attr({text: offset.toFixed(Math.max(-magnitude, 0))});
            }

            offset += step;
        }
    }

    initMouseMarker() {
        let svg_height = this.$svg.height();

        this.mouseMarker = this.s.group().attr({class: 'mouse_marker'});

        let line = this.s.line(0, -10, 0, -svg_height).attr({stroke: 'white', strokeWidth: 1, strokeDasharray: '1 1'});
        this.mouseMarker.add(line);

        let text = this.s.text(0, 40, "").attr({fill: 'white', textAnchor: 'middle'});
        this.mouseMarker.append(text);

        this.s.append(this.mouseMarker);
    }

    updateMouseMarker(x) {
        let svg_height = this.$svg.height();

        let matrix = new Snap.Matrix();
        matrix.translate(x, svg_height);

        this.mouseMarker.transform(matrix);

        let value = this.calculateTimeCoordinate(x);
        this.mouseMarker.select('line').attr({y2: -svg_height});
        this.mouseMarker.select('text').attr({text: value.toPrecision(6)});
    }

    calculateDisplayCoordinate(x, y) {
        let svg_width = this.$svg.width();
        let svg_height = this.$svg.height();

        x -= this.position;
        x *= svg_width / this.zoom;
        x += svg_width / 2;

        y *= svg_height / this.nodeCount;

        return {x: x, y: y};
    }

    calculateTimeCoordinate(x) {
        let svg_width = this.$svg.width();

        x -= svg_width / 2;
        x /= svg_width / this.zoom;
        x += this.position;

        return x;
    }

    initSelection() {
        let svg_height = this.$svg.height();

        this.selectionRect = this.s.rect(0, 0, 0, svg_height).attr({fill: 'white', opacity: 0.2, visibility: 'hidden'});
        this.s.append(this.selectionRect);
    }

    updateSelectionRect() {
        if (this.selection.start !== null) {
            let start, stop;
            if (this.selection.start > this.selection.stop) {
                start = this.selection.stop;
                stop = this.selection.start;
            }
            else {
                start = this.selection.start;
                stop = this.selection.stop;
            }

            let svg_height = this.$svg.height();

            this.selectionRect.attr({
                visibility: 'visible',
                x: this.calculateDisplayCoordinate(start, 0).x,
                width: this.calculateDisplayCoordinate(stop, 0).x - this.calculateDisplayCoordinate(start).x,
                height: svg_height
            });
        }
        else {
            this.selectionRect.attr({visibility: 'hidden'});
        }
    }

    initNodeMarker() {
        this.gNodeMarkers = this.s.group().attr({class: 'node_markers'});
        this.nodeMarkers = [];


        for (let i = 0; i < this.nodeCount; i++) {
            let rect = this.s.rect(-12.5, -12.5, 25, 25).attr({fill: 'white', opacity: 0.8});
            let text = this.s.text(0, 0, i.toString()).attr({
                color: '#333',
                textAnchor: 'middle',
                alignmentBaseline: 'middle'
            });

            let roundText = this.s.text(40, 0, 'round').attr({
                class: 'round',
                fill: 'lightgray',
                alignmentBaseline: 'middle',
                fontSize: '12px'
            });
            let slotText = this.s.text(40, 0, 'slot').attr({
                class: 'slot',
                fill: 'lightgray',
                alignmentBaseline: 'middle',
                fontSize: '12px'
            });
            let gloriaText = this.s.text(40, 0, 'gloria').attr({
                class: 'gloria',
                fill: 'lightgray',
                alignmentBaseline: 'middle',
                fontSize: '12px'
            });

            let group = this.s.group();
            group.add(rect, text, roundText, slotText, gloriaText);

            this.nodeMarkers.push(group);
            this.gNodeMarkers.add(group);
        }

        this.s.append(this.gNodeMarkers);
    }

    updateNodeMarker() {
        let svg_height = this.$svg.height();

        for (let i = 0; i < this.nodeMarkers.length; i++) {
            let matrix = new Snap.Matrix();
            matrix.translate(20, (i + 0.45) / this.nodeCount * svg_height);
            this.nodeMarkers[i].transform(matrix);

            this.nodeMarkers[i].select('.round').attr({y: -svg_height / this.nodeCount * 0.3});
            this.nodeMarkers[i].select('.gloria').attr({y: svg_height / this.nodeCount * 0.3});
        }
    }

    initDescriptors() {
        this.descriptorCount = 200;

        this.gDescriptors = this.s.group().attr({class: 'descriptors'});
        this.descriptors = [];

        for (let i = 0; i < this.descriptorCount; i++) {
            let descriptor = this.s.text(0, 0, "").attr({
                fill: 'white',
                alignmentBaseline: 'middle',
                textAnchor: 'middle',
                fontSize: '12px',
                visibility: 'hidden'
            });

            this.descriptors.push(descriptor);
            this.gDescriptors.add(descriptor);
        }
        this.s.append(this.gNodeMarkers);
    }

    updateDescriptors() {
        let svg_width = this.$svg.width();
        let svg_height = this.$svg.height();
        let descriptorIndex = 0;
        let activityIndex = this.getFirstActivityOnDisplay(this.position - this.zoom / 2, false);

        while (activityIndex < this.trace.activities.length && descriptorIndex < this.descriptorCount) {
            let activity = this.trace.activities[activityIndex];

            let start = Math.max(this.position + -this.zoom / 2, activity.start);
            let end = Math.min(this.position + this.zoom / 2, activity.end);

            if ((end - start) / this.zoom * svg_width < 12) {
                activityIndex += 1;
                continue;
            }

            let text = "";
            let yPos = 0;

            if (activity.activity_type === "LWBRoundActivity") {
                text = `${activity.details.round_type} @ ${this.modulations[activity.details.modulation].name}`;
                yPos -= 0.3;
            }

            else if (activity.activity_type === "LWBSlotActivity") {
                text = activity.details.slot_type;
            }

            else if (activity.activity_type === "CADActivity") {
                text = 'CAD' + (activity.details.success ? '(✓)' : "(✗)");
                yPos += 0.3;
            }

            else if (activity.activity_type === "RxActivity") {
                text = 'Rx' + (activity.details.success ? '(✓)' : "(✗)");
                yPos += 0.3;
            }

            else if (activity.activity_type === "TxActivity") {
                text = 'Tx';
                yPos += 0.3;
            }

            if ((end - start) / this.zoom * svg_width >= 12 * text.length) {
                yPos += activity.node + 0.45;
                yPos *= svg_height / this.nodeCount;

                let xPos = (start + end) / 2;
                xPos = this.calculateDisplayCoordinate(xPos).x;

                this.descriptors[descriptorIndex].attr({x: xPos, y: yPos, text: text, visibility: 'visible'});

                descriptorIndex += 1;
            }

            activityIndex += 1;
        }

        for (let i = descriptorIndex; i < this.descriptorCount; i++) {
            this.descriptors[i].attr({'visibility': 'hidden'});
        }
    }

    drawActivities() {
        this.$svg.empty();

        this.trace.activities.forEach(this.drawActivity.bind(this));
        this.s.append(this.activities);
    }

    drawActivity(activity) {
        let node_offset = activity.node;

        if (activity.activity_type === "LWBRoundActivity") {
            let rect = this.s.rect(activity.start, node_offset, (activity.end - activity.start), 0.9).attr({
                fill: this.modulationsColors[activity.details.modulation]
            });

            this.addTooltip(rect, activity.details.round_type);
            this.activities.add(rect);
        }

        else if (activity.activity_type === "LWBSlotActivity") {
            let rect = this.s.rect(activity.start, (node_offset + 0.3), (activity.end - activity.start), 0.6).attr({
                fill: slot_colors[activity.details.slot_type]
            });

            this.addTooltip(rect, activity.details.slot_type);
            this.activities.add(rect);
        }

        else if (activity.activity_type === "CADActivity") {
            let rect = this.s.rect(activity.start, (node_offset + 0.6), (activity.end - activity.start), 0.3).attr({
                fill: 'blue'
            });

            this.addTooltip(rect, `CAD (${activity.details.success})`);
            this.activities.add(rect);
        }

        else if (activity.activity_type === "RxActivity") {
            let rect = this.s.rect(activity.start, (node_offset + 0.6), (activity.end - activity.start), 0.3).attr({
                fill: 'cornflowerblue'
            });

            this.addTooltip(rect, 'Rx');
            this.activities.add(rect);
        }

        else if (activity.activity_type === "TxActivity") {
            let rect = this.s.rect(activity.start, (node_offset + 0.6), (activity.end - activity.start), 0.3).attr({
                fill: 'crimson'
            });

            this.addTooltip(rect, 'Tx');
            this.activities.add(rect);
        }
    }

    addTooltip(element, text) {
        let tooltip = this.s.el('title');
        tooltip.node.textContent = text;
        element.append(tooltip);
    }


    getActivitiesInSelection() {
        if (this.selection.start > this.selection.stop) {
            let tmp = this.selection.start;
            this.selection.start = this.selection.stop;
            this.selection.stop = tmp;
        }

        let selectedActivities = this.trace.activities.filter(element => {
            return (element.start >= this.selection.start && element.end <= this.selection.stop)
        });

        console.log(selectedActivities);

        for (let i = 0; i < this.nodeCount; i++) {
            let nodeActivities = selectedActivities.filter(element => {
                return (element.node === i);
            });

            let energy = nodeActivities.reduce((accumulator, element) => {
                if (element.energy !== null) {
                    return accumulator + element.energy;
                }
                else {
                    return accumulator;
                }
            }, 0);

            console.log(`Node ${i} energy: ${energy}`);

            selectionCallback
        }
    }

    sortTraceByStart() {
        this.trace.activities.sort((a, b) => {
            if (a.start < b.start) {
                return -1;
            }
            else if (a.start > b.start) {
                return 1;
            }
            else {
                return 0;
            }
        });
    }

    sortTraceByEnd() {
        this.trace.activities.sort((a, b) => {
            if (a.end < b.end) {
                return -1;
            }
            else if (a.end > b.end) {
                return 1;
            }
            else {
                return 0;
            }
        });
    }

    getFirstActivityOnDisplay(position) {
        let range = [0, this.trace.activities.length - 1];
        let mid = (range) => {
            return range[0] + Math.ceil((range[1] - range[0]) / 2);
        };

        let binarySearch = (range) => {
            let value = this.trace.activities[mid(range)].end;
            let nextRange = [];

            if (value > position) {
                nextRange = [range[0], mid(range) - 1];
            }
            else {
                nextRange = [mid(range), range[1]];
            }

            if (nextRange[0] === nextRange[1]) {
                return nextRange[0];
            }
            else {
                return binarySearch(nextRange);
            }
        };

        let index = binarySearch(range);

        /*
        while (index > 0) {
            if (this.trace.activities[index - 1].end > this.position - this.zoom) {
                index -= 1;
            }
            else {
                break;
            }
        }
        */

        return index;
    }
}





