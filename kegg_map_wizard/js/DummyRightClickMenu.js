function Set_toJSON(key, value) {
    if (typeof value === 'object' && value instanceof Set) {
        return [...value];
    }
    return value;
}

function showMapMenu(event, shape) {
    console.log('you clicked on this shape: ', shape)

    let mm = new MapMenu(event, shape)

    const annotations = $(shape).data('annotations')
    const organisms = $(shape).data('organisms')
    const manualNumber = $(shape).data('manual-number')
    const classes = $(shape).attr('class')


    // RAW HTML
    mm.appendElement(`
<h6 class="dropdown-header context-menu-header">
raw HTML:</h6><textarea style="width:100%; font-family: Monospace; font-size:10px; border:0; color: #e83e8c;" disabled
>${shape.outerHTML}</textarea>
`)


    // COVERED ORGANISMS
    if (organisms !== undefined) {
        mm.appendElement(`
<h6 class="dropdown-header context-menu-header">
data-organisms:</h6>
<p class="dropdown-header json">${JSON.stringify(organisms, Set_toJSON, 4)}</p>
`)
    }


    // MANUAL NUMBER
    if (manualNumber !== undefined) {
        mm.appendElement(`
<h6 class="dropdown-header context-menu-header">
data-manual-number:</h6>
<p class="dropdown-header">${manualNumber}</p>
`)
    }


    // ANNOTATIONS
    let annoJsonString = []
    $.each(annotations, function (index) {
        annoJsonString.push(JSON.stringify(this, Set_toJSON, 4))
    })
    annoJsonString = annoJsonString.join(',')

    mm.appendElement(`
<h6 class="dropdown-header context-menu-header">
data-annotations:</h6>
<p class="dropdown-header json">[${annoJsonString}]</p>`)

    // show menu
    mm.show()
}

class MapMenu {
    constructor(event) {
        event.preventDefault()
        event.stopPropagation()
        this.target = event.target
        this.menu_id = 'map-menu'
        this.createMenu(this.menu_id)
        this.dropdown = $('#' + this.menu_id)
        this.popper = null

        this.dropdown_separator_div = $('<div>', {
            class: 'dropdown-divider'
        })
    }

    createMenu = function (id) {
        let new_menu = $('<div>', {
            id: id,
            display: 'flex',
            class: 'ogb-click-menu',
            'aria-labelledby': 'dropdownMenuButton',
        })
        if (!document.getElementById(id)) {
            // create new menu
            new_menu.appendTo('body')
        } else {
            // overwrite menu
            $('#' + id).replaceWith(new_menu)
        }
    }

    appendElement = function (element) {
        this.dropdown.append(element)
    }

    appendSeparator = function () {
        this.dropdown.append(this.dropdown_separator_div)
    }

    appendHeader = function (text) {
        this.dropdown.append($('<h6>', {
                text: text, class: 'dropdown-header context-menu-header'
            })
        )
    }

    // add listener (to close the menu), place and show it.
    show = function (placement = 'bottom') {
        let mydropdown = this.dropdown
        let menu_id = this.menu_id

        // add the click-menu to the page, place it below relative_element
        this.popper = new Popper(this.target, this.dropdown,
            {
                placement: placement,
                modifiers: {
                    eventsEnabled: {enabled: true},
                },
            })

        // add listener to close the menu (only one listener for every menu_id)
        $(document).on('click.context-menu-event', function (e) {

            if (e.altKey || e.metaKey || e.which === 3 || $('#' + menu_id).has(e.target).length == 1 || $('#' + menu_id).is(e.target)) {
                // ignore clicks with alt or meta keys
                // ignore clicks on dropdown
            } else {
                // hide div
                $('#' + menu_id).hide()
            }
        })

        this.dropdown.show()
    }
}