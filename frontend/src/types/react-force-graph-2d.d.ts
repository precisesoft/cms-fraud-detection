declare module "react-force-graph-2d" {
  import { Component } from "react";

  interface NodeObject {
    id: string;
    x?: number;
    y?: number;
    [key: string]: unknown;
  }

  interface LinkObject {
    source: string | NodeObject;
    target: string | NodeObject;
    [key: string]: unknown;
  }

  interface ForceGraph2DProps {
    graphData: { nodes: NodeObject[]; links: LinkObject[] };
    width?: number;
    height?: number;
    nodeLabel?: string | ((node: NodeObject) => string);
    nodeColor?: string | ((node: NodeObject) => string);
    nodeVal?: number | ((node: NodeObject) => number);
    linkLabel?: string | ((link: LinkObject) => string);
    linkColor?: string | ((link: LinkObject) => string);
    linkDirectionalArrowLength?: number;
    linkDirectionalArrowRelPos?: number;
    onNodeClick?: (node: NodeObject, event: MouseEvent) => void;
    cooldownTicks?: number;
    enableZoomInteraction?: boolean;
    enablePanInteraction?: boolean;
    nodeCanvasObject?: (
      node: NodeObject,
      ctx: CanvasRenderingContext2D,
      globalScale: number,
    ) => void;
    nodeCanvasObjectMode?: string | ((node: NodeObject) => string);
    backgroundColor?: string;
    d3Force?: (forceName: string, force?: unknown) => unknown;
  }

  export default class ForceGraph2D extends Component<ForceGraph2DProps> {}
}
