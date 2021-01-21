"use strict"

/**
 * Remove metadata tags from shapes
 *
 * From each shape, remove:
 *   - data-strains
 *   - data-manual-number
 *   - from each annotation in data-annotations:
 *      - 'strains'
 *      - 'manual-number
 *
 * Restores fill/stroke to transparent.
 *
 * @param svg {Object} target svg element
 */
function resetMap(svg) {
    $(svg).find(".shape").each(function (i, shape) {
        // make fill/stroke transparent
        colorShape(shape, 'transparent')
        // empty strains from shape
        $(shape).removeData('strains')
        $(shape).removeData('manual-number')
        // empty strains from annotations
        let annotations = $(shape).data('annotations')
        annotations.forEach(function (annotation, index) {
            delete annotations[index]['strains']
            delete annotations[index]['manual-number']
        })
        $(this).data('annotations', annotations)
    })

    // delete defs element if it exists
    $(svg).find('#shape-color-defs').each(function (i, element) {
        element.remove()
    })
}

/**
 * Colorize shapes by whether they cover certain annotations
 *
 * @param svg {Object} target svg element
 * @param  {string} color The color for covered shapes
 * @param  {Array}  annotations_to_highlight Array of annotations to highlight
 */
function highlightBinary(
    svg,
    color = "red",
    annotations_to_highlight = []  // e.g. ['K00001']
) {
    resetMap(svg)

    $(".shape").each(function () {
        let annotations = $(this).data('annotations')
        if (getCoveredAnnotations(annotations_to_highlight, annotations).length) {
            colorShape(this, color)
        } else {
            colorShape(this, 'transparent')
        }
    })
}

/**
 * Colorize shapes by how many strains have their annotations
 *
 * @param svg {Object} target svg element
 * @param  {Array}  colors Two colors: The first for shapes that are covered by one annotation,
 *   the second for shapes that are covered by all annotations
 * @param  {Object} strains A dictionary { strain => [ annotation ]}
 *   Example: { Strain1: [ "R09127", "R01788", … ], Strain2: [ … ], … }
 *
 * Adds...
 *   - 'data-strains' to shape, for example:
 *        { covering: [ "Strain1", … ], not-covering: [] }
 *   - 'strains' to annotations in 'data-annotations':
 *        { name: "K01223", …, strains: [ "Strain1", … ] }
 *
 * Changes fill/stroke to a color.
 *
 * This data can be removed using resetMap()
 */
function highlightStrains(
    svg,
    strains,
    colors = ['yellow', 'red']
) {
    resetMap(svg)

    let strainNames = Object.keys(strains)
    let colorArray = ['transparent'].concat(chroma.scale(colors).mode('lch').colors(strainNames.length))

    function singleColorShape(shape) {
        let annotations = $(shape).data('annotations')
        let coveringStrains = new Set()
        let notCoveringStrains = new Set()
        annotations.forEach(function (annotation, index) {
            annotations[index]['strains'] = new Set()
        })

        // for each strain, see if it covers anything
        $.each(strains, function (s_name, s_annotations) {
            let covering = false
            annotations.forEach(function (annotation, index) {
                if (s_annotations.includes(annotation['name'])) {
                    annotations[index]['strains'].add(s_name)
                    coveringStrains.add(s_name)
                    covering = true
                }
            })
            if (!covering) {
                notCoveringStrains.add(s_name)
            }

        })

        // write info back to shape
        $(shape).data('strains', {"covering": coveringStrains, "not-covering": notCoveringStrains})
        $(shape).data('annotations', annotations)

        // color shape
        colorShape(shape, colorArray[coveringStrains.size])
    }

    $(".shape").each(function (index) {
        singleColorShape(this)
    })
}

/**
 * Colorize shapes by how many strains have their annotations
 *
 * @param svg {Object} target svg element
 * @param  {Array}  colors Two colors: The first for shapes that are covered by one annotation,
 *   the second for shapes that are covered by all annotations
 * @param  {Object} groupsOfStrains A dictionary of strain dictionaries {group => { strain => [ annotation ]} }
 *   Example: { Group1: { Strain1: [ "R09127", "R01788", … ], Strain2: [ … ], … }, Group2: {…} }
 *
 * Adds...
 *   - 'data-strains' to shape, for example:
 *        { covering: { Group1: [ "Strain1", … ], Group2: []}}, not-covering: { Group1: [], Group2: ["StrainA"] }
 *   - 'strains' to annotations in 'data-annotations':
 *        { name: "K01223", …, strains: [ "Strain1", … ] }
 *   - LinearGradient defs to SVG
 *
 * Changes fill/stroke to a LinearGradient.
 *
 * This data can be removed using resetMap()
 */
function highlightGroupsOfStrains(
    svg,
    groupsOfStrains,
    colors = ['yellow', 'red']
) {
    resetMap(svg)

    const nGroups = Object.keys(groupsOfStrains).length

    // calculate color gradient for all groups of strains
    let groupColorArrays = {}
    for (const [groupName, strains] of Object.entries(groupsOfStrains)) {
        groupColorArrays[groupName] = ['transparent'].concat(chroma.scale(colors).mode('lch').colors(Object.keys(strains).length))
    }

    // create svg defs element to store gradients
    let defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    defs.id = 'shape-color-defs'

    function multicolorShape(shape, shapeIndex) {
        let groupColors = {}
        let annotations = $(shape).data('annotations')
        let coveringStrainGroups = {}
        let notCoveringStrainGroups = {}
        annotations.forEach(function (annotation, index) {
            annotations[index]['strains'] = new Set()
        })

        for (const [groupName, strains] of Object.entries(groupsOfStrains)) {
            let coveringStrains = new Set()
            let notCoveringStrains = new Set()

            // for each strain, see if it covers anything
            $.each(strains, function (s_name, s_annotations) {
                let covering = false
                annotations.forEach(function (annotation, index) {
                    if (s_annotations.includes(annotation['name'])) {
                        annotations[index]['strains'].add(s_name)
                        coveringStrains.add(s_name)
                        covering = true
                    }
                })
                if (!covering) {
                    notCoveringStrains.add(s_name)
                }
            })

            // write info back to shape
            coveringStrainGroups[groupName] = coveringStrains
            notCoveringStrainGroups[groupName] = notCoveringStrains
            groupColors[groupName] = groupColorArrays[groupName][coveringStrains.size]
        }

        // write info back to shape
        $(shape).data('strains', {"covering": coveringStrainGroups, "not-covering": notCoveringStrainGroups})
        $(shape).data('annotations', annotations)

        // color shape
        if (nGroups === 1) {
            colorShape(shape, Object.values(groupColors)[0])
        } else {
            let gradient = createGradient(groupColors, nGroups, shape)
            gradient.id = 'gradient-shape-' + shapeIndex
            defs.appendChild(gradient);
            colorShape(shape, `url(#gradient-shape-${shapeIndex})`)
        }
    }

    $(svg).find(".shape").each(function (index) {
        multicolorShape(this, index)
    })

    svg.appendChild(defs);
}

/**
 * Create a SVG linear gradient
 *
 * @param  {Array}  groupColors A list of colors, one per group
 * @param  {number} nGroups The number of groups
 * @param  {Object} targetElement The element the gradient will be applied to
 * @return {Object} gradient An SVG gradient element
 */
function createGradient(groupColors, nGroups, targetElement) {
    let gradient = document.createElementNS('http://www.w3.org/2000/svg', 'linearGradient');
    const protoStops = Array(nGroups + 1).fill().map((_, index) => index / nGroups * 100 + '%')
    let stops = []
    Object.values(groupColors).forEach(function (color, i) {
        stops.push({'color': color, 'offset': protoStops[i]}, {'color': color, 'offset': protoStops[i + 1]})
    })
    stops.shift()  // remove first element (not important)
    stops.pop()    // remove last element (not important)

    // Create stop elements
    for (var i = 0, length = stops.length; i < length; i++) {
        let stop = document.createElementNS('http://www.w3.org/2000/svg', 'stop')
        stop.setAttribute('offset', stops[i].offset);
        stop.setAttribute('stop-color', stops[i].color);
        gradient.appendChild(stop);
    }

    // set gradient direction
    // gradient.setAttribute('x2', '1') // ->  does not work for elements with width or height = 0, wtf?!
    const bbox = targetElement.getBBox()
    gradient.setAttribute('gradientUnits', 'userSpaceOnUse')
    gradient.setAttribute('x1', bbox['x'])
    gradient.setAttribute('x2', bbox['x'] + bbox['width'])

    return gradient
}


/**
 * Colorize shapes by continuous numbers between 0 and 1
 *
 * @param svg {Object} target svg element
 * @param  {Array}  colors Two colors: The first for shapes that are covered by one annotation,
 *   the second for shapes that are covered by all annotations
 * @param  {Object} annotation_to_number A dictionary { annotation => number }
 *   Example: { C00033: 0.24, C00031: 0.53, … }
 *
 * Adds...
 *   - 'data-manual-number' to shape, for example:
 *        0.87
 *   - 'manual-number' to annotations in 'data-annotations':
 *        { name: "K01223", …, manual-number: 0.87 }
 *
 * Changes fill to a color.
 *
 * This data can be removed using resetMap()
 */
function highlightContinuous(
    svg,
    annotation_to_number,
    colors = ['yellow', 'red']
) {
    resetMap(svg)

    const myAnnotations = Object.keys(annotation_to_number)

    function manualShape(shape) {
        let annotations = $(shape).data('annotations')
        let manualNumber

        // for each strain, see if it covers anything
        annotations.forEach(function (annotation, index) {
            if (myAnnotations.includes(annotation['name'])) {
                manualNumber = annotation_to_number[annotation['name']]
                annotations[index]['manual-number'] = manualNumber
            }
        })

        if (typeof manualNumber === 'undefined') {
            return  // do nothing
        }

        // write info back to shape
        $(shape).data('manual-number', manualNumber)
        $(shape).data('annotations', annotations)

        // color shape
        colorShape(shape, chroma.mix(colors[0], colors[1], manualNumber))
    }

    $(".shape").each(function (index) {
        manualShape(this)
    })
}

/**
 * Changes the fill or stroke attribute of a shape.
 *
 * The value is set to the attribute specified by 'data-apply-color-to'.
 * If 'data-apply-color-to' is not set, the 'fill' attribute will be changed.
 *
 * @param  {Object} shape Shape svg element
 * @param  {string} attributeValue color or url to definition, e.g. 'red' or 'url(#gradient-shape-0)'
 */
function colorShape(shape, attributeValue) {
    let targetAttribute = $(shape).data('apply-color-to')
    targetAttribute = targetAttribute === undefined ? 'fill' : targetAttribute
    shape.setAttribute(targetAttribute, attributeValue)
}

/**
 * Returns the annotations that are covered by the shape
 *
 * @param  {Array}  StrainAnnotations Array of annotations, e.g. [ "C00033", "C00031", … ]
 * @param  {Object} ShapeAnnotations Array of shape-annotation-objects [ { name="K03103" }, … ]
 * @return {Array}  Array of annotations that are covered by the shape
 */
function getCoveredAnnotations(StrainAnnotations, ShapeAnnotations) {
    return ShapeAnnotations.filter(item => StrainAnnotations.includes(item['name']))
}

/**
 * Opens save-as dialog
 *
 * @param  {string} uri Content to download
 * @param  {string} filename Desired filename
 */
function saveUriAs(uri, filename) {
    var link = document.createElement('a')
    if (typeof link.download === 'string') {
        link.href = uri
        link.download = filename
        //Firefox requires the link to be in the body
        document.body.appendChild(link)
        //simulate click
        link.click()
        //remove the link when done
        document.body.removeChild(link)
    } else {
        window.open(uri)
    }
}

/**
 * Save a map as png, opens save-as dialog
 *
 * @param  {Object} element Div to save as png
 */
function savePng(element) {
    $(window).scrollTop(0)  // otherwise, png will be cropped.
    html2canvas(element).then(function (canvas) {
        saveUriAs(canvas.toDataURL(), 'pathway.png')
    })
}

/**
 * Save a map as svg, opens save-as dialog
 *
 * @param svg {Object} target svg element
 */
function saveSvg(svg) {
    //serialize svg.
    let serializer = new XMLSerializer()
    let data = serializer.serializeToString(svg)

    data = encodeURIComponent(data)

    // add file type declaration
    data = "data:image/svg+xml;charset=utf-8," + data

    saveUriAs(data, 'pathway.svg')
}