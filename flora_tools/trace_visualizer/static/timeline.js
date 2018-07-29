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

        this.initBoundaries();
        this.modulations = this.trace.network.modulations;
        this.modulationsColors = this.modulations.map(modulation => {
            return `rgba(${modulation.color[0] * 255}, ${modulation.color[1] * 255}, ${modulation.color[2] * 255}, ${modulation.color[3]})`
        });

        this.drawTrace();

        this.register_mouse_interaction();
    }

    register_mouse_interaction() {
        let isPanning = false;
        let lastMousePosition = null;

        this.$svg.mousemove(event => {
            let x = event.pageX - this.$svg.offset().left;
            let y = event.pageY - this.$svg.offset().top;

            if (isPanning && lastMousePosition !== null) {
                let dx = x - lastMousePosition.x;
                let dy = y - lastMousePosition.y;
                let pixel_width = this.$svg.width();
                this.position -= (dx / pixel_width) * this.zoom;
                this.updateViewbox();
            }

            lastMousePosition = {x: x, y: y};
            event.stopPropagation();
        });

        this.$svg.mousedown(event => {
            isPanning = true;
        });

        this.$svg.mouseup(event => {
            isPanning = false;
        });

        this.$svg.mouseleave(event => {
            isPanning = false;
        });

        this.$svg.on('mousewheel', event => {
            let dZoom = Math.exp(-event.originalEvent.wheelDelta / 240);
            let fixedX = (event.pageX - this.$svg.offset().left) / this.$svg.width();
            let fixedPosition = this.position - (0.5 - fixedX) * this.zoom;

            this.position = fixedPosition + this.zoom * dZoom * (0.5 - fixedX);
            this.zoom *= dZoom;

            this.updateViewbox();
            event.stopPropagation();
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

        this.s.attr({viewBox:`${x},${y},${wi},${hi}`});
    }


    drawTrace() {
        this.$svg.empty();

        this.trace.activities.forEach(this.drawActivity.bind(this))
    }

    drawActivity(activity) {
        let node_offset = activity.node;

        if (activity.activity_type === "LWBRoundActivity") {
            let rect = this.s.rect(activity.start, node_offset, (activity.end - activity.start), 0.9).attr({
                fill: this.modulationsColors[activity.details.modulation]
            });

            this.addTooltip(rect, activity.details.round_type);
        }

        else if (activity.activity_type === "LWBSlotActivity") {
            let rect = this.s.rect(activity.start, (node_offset + 0.3), (activity.end - activity.start), 0.6).attr({
                fill: slot_colors[activity.details.slot_type]
            });

            this.addTooltip(rect, activity.details.slot_type);
        }

        else if (activity.activity_type === "CADActivity") {
            let rect = this.s.rect(activity.start, (node_offset + 0.6), (activity.end - activity.start), 0.3).attr({
                fill: 'blue'
            });

            this.addTooltip(rect, `CAD (${activity.details.success})`);
        }

        else if (activity.activity_type === "RxActivity") {
            let rect = this.s.rect(activity.start, (node_offset + 0.6), (activity.end - activity.start), 0.3).attr({
                fill: 'cornflowerblue'
            });

            this.addTooltip(rect, 'Rx');
        }

        else if (activity.activity_type === "TxActivity") {
            let rect =this.s.rect(activity.start, (node_offset + 0.6), (activity.end - activity.start), 0.3).attr({
                fill: 'crimson'
            });

            this.addTooltip(rect, 'Tx');
        }
    }

    addTooltip(element, text) {
        let tooltip = this.s.el('title');
        tooltip.node.textContent = text;
        element.append(tooltip);
    }
}





