import overall from './tiles/overall/manifest.json'
import floor1Lobby from './tiles/floor-1-lobby/manifest.json'
import floor1Reading from './tiles/floor-1-reading/manifest.json'
import floor2Children from './tiles/floor-2-children/manifest.json'
import floor3 from './tiles/floor-3/manifest.json'
import floor4 from './tiles/floor-4/manifest.json'
import floor5 from './tiles/floor-5/manifest.json'
import floor6 from './tiles/floor-6/manifest.json'
import floor7Screening from './tiles/floor-7-screening/manifest.json'

export const FLOOR_CONFIG = {
  project: {
    title: '《图书馆》',
    description: '图书馆建筑可视化导览',
  },
  floors: [
    {
      id: 'overall',
      name: '整体外观',
      manifest: overall,
      viewMinZoom: 1.5,
      viewMaxZoom: 5,
      markers: [{
        id: 'pano-overall',
        position: [8192, 8192],
        title: '正门全景',
        color: 'red',
        label: ['360°全景'],
        text: '正门360°全景入口',
        sceneUrl: 'https://360.acloud.uno/?scene=scene1',
      }],
      annotations: [],
    },
    {
      id: 'floor-1-lobby',
      name: '1F 大厅',
      manifest: floor1Lobby,
      viewMinZoom: 1.25,
      viewMaxZoom: 5,
      markers: [{
        id: 'pano-lobby',
        position: [8192, 8192],
        title: '大厅全景',
        color: 'red',
        label: ['360°全景'],
        text: '一楼大厅360°全景入口',
        sceneUrl: 'https://360.acloud.uno/?scene=scene2',
      }],
      annotations: [],
    },
    {
      id: 'floor-1-reading',
      name: '1F 阅览室',
      manifest: floor1Reading,
      viewMinZoom: 1.25,
      viewMaxZoom: 5,
      markers: [],
      annotations: [],
    },
    {
      id: 'floor-2-children',
      name: '2F 儿童区',
      manifest: floor2Children,
      viewMinZoom: 1.25,
      viewMaxZoom: 5,
      markers: [],
      annotations: [],
    },
    {
      id: 'floor-3',
      name: '3F',
      manifest: floor3,
      viewMinZoom: 1.25,
      viewMaxZoom: 5,
      markers: [{
        id: 'pano-floor3',
        position: [8192, 8192],
        title: '三楼全景',
        color: 'red',
        label: ['360°全景'],
        text: '三楼阅览区360°全景入口',
        sceneUrl: 'https://360.acloud.uno/?scene=scene3',
      }],
      annotations: [],
    },
    {
      id: 'floor-4',
      name: '4F',
      manifest: floor4,
      viewMinZoom: 1.25,
      viewMaxZoom: 5,
      markers: [],
      annotations: [],
    },
    {
      id: 'floor-5',
      name: '5F',
      manifest: floor5,
      viewMinZoom: 1.25,
      viewMaxZoom: 5,
      markers: [],
      annotations: [],
    },
    {
      id: 'floor-6',
      name: '6F',
      manifest: floor6,
      viewMinZoom: 1.25,
      viewMaxZoom: 5,
      markers: [],
      annotations: [],
    },
    {
      id: 'floor-7-screening',
      name: '7F 放映厅',
      manifest: floor7Screening,
      viewMinZoom: 2.5,
      viewMaxZoom: 5,
      markers: [],
      annotations: [],
    },
  ],
}
