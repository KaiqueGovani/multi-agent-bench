export type Point = { x: number; y: number };
export type CardRect = Point & { width: number; height: number };

const GAP = 6;
const CLEARANCE = 16;

function center(rect: CardRect): Point {
  return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
}

function borderPoint(rect: CardRect, toward: Point): Point {
  const origin = center(rect);
  const dx = toward.x - origin.x;
  const dy = toward.y - origin.y;
  const distance = Math.hypot(dx, dy) || 1;
  const ratio = 1 / (Math.max(Math.abs(dx) / (rect.width / 2), Math.abs(dy) / (rect.height / 2)) || 1);
  return { x: origin.x + dx * ratio + dx / distance * GAP, y: origin.y + dy * ratio + dy / distance * GAP };
}

/** Test the open rectangle: paths may touch a routing corner, never enter a card. */
function crossesCard(from: Point, to: Point, rect: CardRect): boolean {
  let enter = 0;
  let leave = 1;
  for (const [start, delta, low, high] of [
    [from.x, to.x - from.x, rect.x - 2, rect.x + rect.width + 2],
    [from.y, to.y - from.y, rect.y - 2, rect.y + rect.height + 2],
  ]) {
    if (Math.abs(delta) < 0.001) {
      if (start <= low || start >= high) return false;
    } else {
      const a = (low - start) / delta;
      const b = (high - start) / delta;
      enter = Math.max(enter, Math.min(a, b));
      leave = Math.min(leave, Math.max(a, b));
    }
  }
  return enter < leave - 0.001 && leave > 0.001 && enter < 0.999;
}

function roundedPath(points: Point[]): string {
  let path = `M ${points[0].x},${points[0].y}`;
  for (let index = 1; index < points.length - 1; index++) {
    const before = points[index - 1];
    const corner = points[index];
    const after = points[index + 1];
    const incoming = Math.hypot(corner.x - before.x, corner.y - before.y);
    const outgoing = Math.hypot(after.x - corner.x, after.y - corner.y);
    const radius = Math.min(8, incoming / 3, outgoing / 3);
    const a = { x: corner.x + (before.x - corner.x) * radius / incoming, y: corner.y + (before.y - corner.y) * radius / incoming };
    const b = { x: corner.x + (after.x - corner.x) * radius / outgoing, y: corner.y + (after.y - corner.y) * radius / outgoing };
    path += ` L ${a.x},${a.y} Q ${corner.x},${corner.y} ${b.x},${b.y}`;
  }
  const end = points.at(-1)!;
  return `${path} L ${end.x},${end.y}`;
}

/** Float endpoints on the facing card borders and route around intervening cards. */
export function routeSwarmEdge(source: CardRect, target: CardRect, cards: CardRect[]) {
  const start = borderPoint(source, center(target));
  const end = borderPoint(target, center(source));
  const visible = (a: Point, b: Point) => !cards.some((card) => crossesCard(a, b, card));
  if (visible(start, end)) return { path: roundedPath([start, end]), detour: false };

  // A small visibility graph is enough for the five-peer roster. Corners have
  // extra clearance so rounded bends and arrowheads remain outside the cards.
  const points = [start, end, ...cards.flatMap((card) => [
    { x: card.x - CLEARANCE, y: card.y - CLEARANCE },
    { x: card.x + card.width + CLEARANCE, y: card.y - CLEARANCE },
    { x: card.x + card.width + CLEARANCE, y: card.y + card.height + CLEARANCE },
    { x: card.x - CLEARANCE, y: card.y + card.height + CLEARANCE },
  ])];
  const distances = points.map(() => Infinity);
  const previous = points.map(() => -1);
  const visited = new Set<number>();
  distances[0] = 0;
  while (visited.size < points.length) {
    let current = -1;
    for (let index = 0; index < points.length; index++) {
      if (!visited.has(index) && (current < 0 || distances[index] < distances[current])) current = index;
    }
    if (current < 0 || distances[current] === Infinity || current === 1) break;
    visited.add(current);
    for (let next = 0; next < points.length; next++) {
      if (visited.has(next) || next === current || !visible(points[current], points[next])) continue;
      // A small turn cost keeps routes simple when several corridors are alike.
      const distance = distances[current] + Math.hypot(points[next].x - points[current].x, points[next].y - points[current].y) + (current === 0 ? 0 : 12);
      if (distance < distances[next]) {
        distances[next] = distance;
        previous[next] = current;
      }
    }
  }
  const route = [end];
  let index = previous[1];
  while (index >= 0) {
    route.unshift(points[index]);
    index = previous[index];
  }
  return { path: roundedPath(route.length > 1 ? route : [start, end]), detour: true };
}
