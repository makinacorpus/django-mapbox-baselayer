(function() {
    'use strict';
    function init() {
        var typeField = document.getElementById('id_base_layer_type');
        if (!typeField) return;

        var styleUrlRow = document.querySelector('.field-style_url');
        var tileSizeRow = document.querySelector('.field-tile_size');
        var tileInline = document.getElementById('tiles-group');
        var spriteRow = document.querySelector('.field-sprite');
        var glyphsRow = document.querySelector('.field-glyphs');

        function toggleFields() {
            var type = typeField.value;
            if (type === 'raster') {
                if (styleUrlRow) styleUrlRow.style.display = 'none';
                if (tileSizeRow) tileSizeRow.style.display = '';
                if (tileInline) tileInline.style.display = '';
                if (spriteRow) spriteRow.style.display = '';
                if (glyphsRow) glyphsRow.style.display = '';
            } else if (type === 'mapbox') {
                if (styleUrlRow) styleUrlRow.style.display = '';
                if (tileSizeRow) tileSizeRow.style.display = 'none';
                if (tileInline) tileInline.style.display = 'none';
                if (spriteRow) spriteRow.style.display = '';
                if (glyphsRow) glyphsRow.style.display = '';
            } else {
                if (styleUrlRow) styleUrlRow.style.display = 'none';
                if (tileSizeRow) tileSizeRow.style.display = 'none';
                if (tileInline) tileInline.style.display = 'none';
                if (spriteRow) spriteRow.style.display = 'none';
                if (glyphsRow) glyphsRow.style.display = 'none';
            }
        }

        typeField.addEventListener('change', toggleFields);
        toggleFields();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
