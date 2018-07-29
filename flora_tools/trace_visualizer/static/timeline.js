const slot_colors = {
    SYNC: 'fuchsia',
    ROUND_SCHEDULE: 'rebeccapurple',
    CONTENTION: 'lightcoral',
    SLOT_SCHEDULE: 'darkorchid',
    DATA: 'deepskyblue',
    ACK: 'mediumaquamarine',
};

export class Timeline {
    constructor(svg, trace) {
        this.svg = svg;
        this.$svg = $(svg);

        this.trace = trace;
        console.log(this.trace);

        this.s = Snap(svg);

        this.modulations = this.trace.network.modulations;
        this.modulationsColors = this.modulations.map(modulation => {
            return `rgba(${modulation.color[0] * 255}, ${modulation.color[1] * 255}, ${modulation.color[2] * 255}, ${modulation.color[3]})`
        });

        this.selection = {start: null, stop: null};

        this.initActivities();
        this.drawActivities();

        this.initSelection();

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

            if (this.zoom > 0.0001 || dZoom >= 1) {
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

        $('body').resize(vent => {
            this.updateViewbox();
        });
    }

    initBoundaries() {
        this.s.attr({'preserveAspectRatio': 'none'});

        this.nodeCount = this.trace.network.nodes.length;
        this.begin = this.trace.activities[0].start;
        this.end = this.trace.activities[this.trace.activities.length - 1].end;

        this.position = (this.begin + this.end) / 2;
        this.zoom = (this.end - this.begin);

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

            if (element.start >= this.selection.start && element.end <= this.selection.stop) {
                return true;
            }
            else {
                return false;
            }
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
        }
    }

}





