// D3.js visualization module
class DataVisualizer {
    constructor(containerId) {
        this.container = d3.select(`#${containerId}`);
        this.margin = {top: 40, right: 40, bottom: 60, left: 60};
        this.width = 600 - this.margin.left - this.margin.right;
        this.height = 400 - this.margin.top - this.margin.bottom;
        
        // Create tooltip div
        this.tooltip = d3.select("body").append("div")
            .attr("class", "tooltip")
            .style("opacity", 0);
    }

    render(config) {
        this.container.html(''); // Clear previous visualization
        
        // Set chart title
        d3.select("#chart-title").text(this.generateChartTitle(config));
        
        switch(config.type) {
            case 'line_chart':
                this.renderLineChart(config);
                break;
            case 'bar_chart_vertical':
                this.renderBarChart(config, false);
                break;
            case 'bar_chart_horizontal':
                this.renderBarChart(config, true);
                break;
            case 'scatter_plot':
                this.renderScatterPlot(config);
                break;
            case 'bubble_chart':
                this.renderBubbleChart(config);
                break;
            case 'pie_chart':
                this.renderPieChart(config);
                break;
            case 'bar_histogram':
                this.renderHistogram(config);
                break;
            default:
                this.container.html('<p>No suitable visualization available</p>');
        }
    }

    generateChartTitle(config) {
        const type = config.type.replace(/_/g, ' ').split(' ')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
        return `${type} Visualization`;
    }

    renderLineChart(config) {
        const svg = this.createSvg();
        const data = config.config.data;
        const mapping = config.config.mapping;

        // Create scales with padding
        const x = d3.scaleTime()
            .domain(d3.extent(data, d => new Date(d[mapping.x])))
            .range([0, this.width])
            .nice();

        const y = d3.scaleLinear()
            .domain([0, d3.max(data, d => d[mapping.y]) * 1.1])
            .range([this.height, 0])
            .nice();

        // Add line with transition
        const line = d3.line()
            .x(d => x(new Date(d[mapping.x])))
            .y(d => y(d[mapping.y]))
            .curve(d3.curveMonotoneX);

        const path = svg.append("path")
            .datum(data)
            .attr("fill", "none")
            .attr("stroke", "steelblue")
            .attr("stroke-width", 2)
            .attr("d", line);

        // Add dots
        const dots = svg.selectAll(".dot")
            .data(data)
            .enter().append("circle")
            .attr("class", "dot")
            .attr("cx", d => x(new Date(d[mapping.x])))
            .attr("cy", d => y(d[mapping.y]))
            .attr("r", 5)
            .style("fill", "steelblue")
            .style("opacity", 0.7)
            .on("mouseover", (event, d) => {
                this.tooltip.transition()
                    .duration(200)
                    .style("opacity", .9);
                this.tooltip.html(
                    `Date: ${new Date(d[mapping.x]).toLocaleDateString()}<br/>
                     Value: ${d[mapping.y]}`
                )
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 28) + "px");
            })
            .on("mouseout", () => {
                this.tooltip.transition()
                    .duration(500)
                    .style("opacity", 0);
            });

        // Add axes with transitions
        this.addAxes(svg, x, y, mapping);
    }

    renderBarChart(config, horizontal = false) {
        const svg = this.createSvg();
        const data = config.config.data;
        const mapping = config.config.mapping;

        const x = horizontal ? 
            d3.scaleLinear().range([0, this.width]) :
            d3.scaleBand().range([0, this.width]).padding(0.2);

        const y = horizontal ?
            d3.scaleBand().range([0, this.height]).padding(0.2) :
            d3.scaleLinear().range([this.height, 0]);

        // Set domains based on orientation
        if (horizontal) {
            x.domain([0, d3.max(data, d => d[mapping.x]) * 1.1]);
            y.domain(data.map(d => d[mapping.y]));
        } else {
            x.domain(data.map(d => d[mapping.x]));
            y.domain([0, d3.max(data, d => d[mapping.y]) * 1.1]);
        }

        // Add bars with transitions and interactions
        const bars = svg.selectAll(".bar")
            .data(data)
            .enter().append("rect")
            .attr("class", "bar")
            .style("fill", "steelblue")
            .on("mouseover", (event, d) => {
                d3.select(event.currentTarget)
                    .transition()
                    .duration(200)
                    .style("fill", "#45a049");
                
                this.tooltip.transition()
                    .duration(200)
                    .style("opacity", .9);
                this.tooltip.html(
                    `${mapping.x}: ${d[mapping.x]}<br/>
                     ${mapping.y}: ${d[mapping.y]}`
                )
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 28) + "px");
            })
            .on("mouseout", (event) => {
                d3.select(event.currentTarget)
                    .transition()
                    .duration(200)
                    .style("fill", "steelblue");
                
                this.tooltip.transition()
                    .duration(500)
                    .style("opacity", 0);
            });

        // Set bar attributes based on orientation
        if (horizontal) {
            bars.attr("y", d => y(d[mapping.y]))
                .attr("height", y.bandwidth())
                .attr("x", 0)
                .transition()
                .duration(1000)
                .attr("width", d => x(d[mapping.x]));
        } else {
            bars.attr("x", d => x(d[mapping.x]))
                .attr("width", x.bandwidth())
                .attr("y", this.height)
                .attr("height", 0)
                .transition()
                .duration(1000)
                .attr("y", d => y(d[mapping.y]))
                .attr("height", d => this.height - y(d[mapping.y]));
        }

        this.addAxes(svg, x, y, mapping, horizontal);
    }

    renderScatterPlot(config) {
        const svg = this.createSvg();
        const data = config.config.data;
        const mapping = config.config.mapping;

        const x = d3.scaleLinear()
            .domain(d3.extent(data, d => d[mapping.x]))
            .range([0, this.width])
            .nice();

        const y = d3.scaleLinear()
            .domain(d3.extent(data, d => d[mapping.y]))
            .range([this.height, 0])
            .nice();

        svg.selectAll("circle")
            .data(data)
            .enter()
            .append("circle")
            .attr("cx", d => x(d[mapping.x]))
            .attr("cy", d => y(d[mapping.y]))
            .attr("r", 5)
            .attr("fill", "steelblue")
            .attr("opacity", 0.7)
            .on("mouseover", (event, d) => {
                d3.select(event.currentTarget)
                    .transition()
                    .duration(200)
                    .attr("r", 8)
                    .attr("opacity", 1);
                
                this.tooltip.transition()
                    .duration(200)
                    .style("opacity", .9);
                this.tooltip.html(
                    `${mapping.x}: ${d[mapping.x]}<br/>
                     ${mapping.y}: ${d[mapping.y]}`
                )
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 28) + "px");
            })
            .on("mouseout", (event) => {
                d3.select(event.currentTarget)
                    .transition()
                    .duration(200)
                    .attr("r", 5)
                    .attr("opacity", 0.7);
                
                this.tooltip.transition()
                    .duration(500)
                    .style("opacity", 0);
            });

        this.addAxes(svg, x, y, mapping);
    }

    renderBubbleChart(config) {
        const svg = this.createSvg();
        const data = config.config.data;
        const mapping = config.config.mapping;

        const x = d3.scaleLinear()
            .domain(d3.extent(data, d => d[mapping.x]))
            .range([0, this.width])
            .nice();

        const y = d3.scaleLinear()
            .domain(d3.extent(data, d => d[mapping.y]))
            .range([this.height, 0])
            .nice();

        const size = d3.scaleLinear()
            .domain(d3.extent(data, d => d[mapping.size]))
            .range([4, 20]);

        svg.selectAll("circle")
            .data(data)
            .enter()
            .append("circle")
            .attr("cx", d => x(d[mapping.x]))
            .attr("cy", d => y(d[mapping.y]))
            .attr("r", d => size(d[mapping.size]))
            .attr("fill", "steelblue")
            .attr("opacity", 0.7)
            .on("mouseover", (event, d) => {
                d3.select(event.currentTarget)
                    .transition()
                    .duration(200)
                    .attr("opacity", 1)
                    .attr("r", d => size(d[mapping.size]) * 1.2);
                
                this.tooltip.transition()
                    .duration(200)
                    .style("opacity", .9);
                this.tooltip.html(
                    `${mapping.x}: ${d[mapping.x]}<br/>
                     ${mapping.y}: ${d[mapping.y]}<br/>
                     Size: ${d[mapping.size]}`
                )
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 28) + "px");
            })
            .on("mouseout", (event, d) => {
                d3.select(event.currentTarget)
                    .transition()
                    .duration(200)
                    .attr("opacity", 0.7)
                    .attr("r", d => size(d[mapping.size]));
                
                this.tooltip.transition()
                    .duration(500)
                    .style("opacity", 0);
            });

        this.addAxes(svg, x, y, mapping);
    }

    renderPieChart(config) {
        const svg = this.createSvg();
        const data = config.config.data;
        const mapping = config.config.mapping;

        const radius = Math.min(this.width, this.height) / 2;
        const g = svg.append("g")
            .attr("transform", `translate(${this.width/2},${this.height/2})`);

        const color = d3.scaleOrdinal(d3.schemeCategory10);

        const pie = d3.pie()
            .value(d => d[mapping.value]);

        const path = d3.arc()
            .outerRadius(radius - 10)
            .innerRadius(0);

        const labelArc = d3.arc()
            .outerRadius(radius - 40)
            .innerRadius(radius - 40);

        const arc = g.selectAll(".arc")
            .data(pie(data))
            .enter().append("g")
            .attr("class", "arc");

        arc.append("path")
            .attr("d", path)
            .attr("fill", (d, i) => color(i))
            .style("stroke", "white")
            .style("stroke-width", "2px")
            .on("mouseover", (event, d) => {
                d3.select(event.currentTarget)
                    .transition()
                    .duration(200)
                    .attr("transform", "scale(1.05)");
                
                this.tooltip.transition()
                    .duration(200)
                    .style("opacity", .9);
                this.tooltip.html(
                    `${mapping.category}: ${d.data[mapping.category]}<br/>
                     Value: ${d.data[mapping.value]}`
                )
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 28) + "px");
            })
            .on("mouseout", (event) => {
                d3.select(event.currentTarget)
                    .transition()
                    .duration(200)
                    .attr("transform", "scale(1)");
                
                this.tooltip.transition()
                    .duration(500)
                    .style("opacity", 0);
            });

        // Add labels
        arc.append("text")
            .attr("transform", d => `translate(${labelArc.centroid(d)})`)
            .attr("dy", ".35em")
            .style("text-anchor", "middle")
            .text(d => d.data[mapping.category]);
    }

    renderHistogram(config) {
        const svg = this.createSvg();
        const data = config.config.data;
        const mapping = config.config.mapping;

        const x = d3.scaleLinear()
            .domain(d3.extent(data, d => d[mapping.value]))
            .range([0, this.width])
            .nice();

        const histogram = d3.histogram()
            .value(d => d[mapping.value])
            .domain(x.domain())
            .thresholds(x.ticks(20));

        const bins = histogram(data);

        const y = d3.scaleLinear()
            .domain([0, d3.max(bins, d => d.length)])
            .range([this.height, 0])
            .nice();

        const bars = svg.selectAll("rect")
            .data(bins)
            .enter()
            .append("rect")
            .attr("x", d => x(d.x0))
            .attr("width", d => Math.max(0, x(d.x1) - x(d.x0) - 1))
            .attr("y", d => y(d.length))
            .attr("height", d => this.height - y(d.length))
            .attr("fill", "steelblue")
            .on("mouseover", (event, d) => {
                d3.select(event.currentTarget)
                    .transition()
                    .duration(200)
                    .style("fill", "#45a049");
                
                this.tooltip.transition()
                    .duration(200)
                    .style("opacity", .9);
                this.tooltip.html(
                    `Range: ${d.x0.toFixed(2)} - ${d.x1.toFixed(2)}<br/>
                     Count: ${d.length}`
                )
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 28) + "px");
            })
            .on("mouseout", (event) => {
                d3.select(event.currentTarget)
                    .transition()
                    .duration(200)
                    .style("fill", "steelblue");
                
                this.tooltip.transition()
                    .duration(500)
                    .style("opacity", 0);
            });

        // Create custom mapping object for histogram
        const histogramMapping = {
            x: "Value",
            y: "Frequency"
        };

        this.addAxes(svg, x, y, histogramMapping);
    }

    createSvg() {
        return this.container.append("svg")
            .attr("width", this.width + this.margin.left + this.margin.right)
            .attr("height", this.height + this.margin.top + this.margin.bottom)
            .append("g")
            .attr("transform", `translate(${this.margin.left},${this.margin.top})`);
    }

    addAxes(svg, x, y, mapping, horizontal = false) {
        // Add X axis with transition
        const xAxis = svg.append("g")
            .attr("class", "x-axis")
            .attr("transform", `translate(0,${this.height})`)
            .call(d3.axisBottom(x));

        // Add Y axis with transition
        const yAxis = svg.append("g")
            .attr("class", "y-axis")
            .call(d3.axisLeft(y));

        // Add labels
        svg.append("text")
            .attr("class", "x-label")
            .attr("text-anchor", "middle")
            .attr("x", this.width / 2)
            .attr("y", this.height + 40)
            .text(mapping.x);

        svg.append("text")
            .attr("class", "y-label")
            .attr("text-anchor", "middle")
            .attr("transform", "rotate(-90)")
            .attr("y", -40)
            .attr("x", -this.height / 2)
            .text(mapping.y);
    }
} 