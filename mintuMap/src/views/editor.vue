<template>
  <Editor :floors="floorList" />
</template>

<script setup>
import Editor from '@/components/MarkerEditor1.vue'
import { FLOOR_CONFIG } from '@/data/floors'

const floorList = FLOOR_CONFIG.floors.map(f => ({
  id: f.id,
  name: f.name,
  manifestUrl: `/tiles/${f.id}/manifest.json`,
  viewMinZoom: f.viewMinZoom,
  viewMaxZoom: f.viewMaxZoom,
}))
</script>
