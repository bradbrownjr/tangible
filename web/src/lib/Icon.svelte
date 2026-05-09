<!-- Thin wrapper around lucide-svelte icon components.
     Usage: <Icon name="trash-2" size={18} />
            <Icon name="check" aria-label="Saved" />

     Only the icons listed in ICON_MAP are bundled. Add new icons here
     when introducing new <Icon name="..."> calls elsewhere in the app.
     (Named imports keep the build output small vs. `import * as lucide`.) -->
<script lang="ts">
    import {
        Activity, ArrowDown, ArrowUp, BatteryCharging, Bell, BookOpen, Box, Building,
        CalendarCheck, CalendarClock, CalendarX,
        Car, Check, CheckCircle, ChevronDown, ChevronUp, CircleX,
        ChevronLeft, ChevronRight, CircleAlert, Clock, CornerDownRight,
        DatabaseBackup, Dice5, DoorOpen, Download, Eye, EyeOff, File, FileArchive, FileCog, FileSpreadsheet,
        Film, FlaskConical, Folder, Gamepad2, Grid2x2, Home, House, Image, Inbox, Info, Link2Off, List,
        Loader, MapPin, Menu, MoreHorizontal, Music,
        Nut, Package, PackageCheck, PackageX, PartyPopper,
        Palette, Pencil, Settings, Settings2, Share2, Shield, ShoppingCart, Shirt,
        SlidersHorizontal, Sparkles, Star, Store,
        Trash2, TriangleAlert, Upload, User, Users, Wrench, X,
    } from 'lucide-svelte';

    const ICON_MAP: Record<string, any> = {
        'activity': Activity, 'arrow-down': ArrowDown, 'arrow-up': ArrowUp,
        'battery-charging': BatteryCharging, 'bell': Bell, 'book-open': BookOpen, 'box': Box, 'building': Building,
        'calendar-check': CalendarCheck, 'calendar-clock': CalendarClock, 'calendar-x': CalendarX,
        'car': Car, 'check': Check,
        'check-circle': CheckCircle, 'chevron-down': ChevronDown, 'chevron-up': ChevronUp, 'circle-x': CircleX,
        'chevron-left': ChevronLeft, 'chevron-right': ChevronRight,
        'circle-alert': CircleAlert, 'clock': Clock, 'corner-down-right': CornerDownRight,
        'database-backup': DatabaseBackup, 'dice-5': Dice5, 'door-open': DoorOpen, 'download': Download,
        'eye': Eye, 'eye-off': EyeOff,
        'file': File, 'file-archive': FileArchive, 'file-cog': FileCog, 'file-spreadsheet': FileSpreadsheet,
        'film': Film, 'flask-conical': FlaskConical, 'folder': Folder,
        'gamepad-2': Gamepad2, 'grid-2x2': Grid2x2,
        'home': Home, 'house': House, 'image': Image, 'inbox': Inbox, 'info': Info, 'list': List,
        'link-2-off': Link2Off, 'loader': Loader,
        'map-pin': MapPin, 'menu': Menu, 'more-horizontal': MoreHorizontal, 'music': Music,
        'nut': Nut, 'package': Package, 'package-check': PackageCheck, 'package-x': PackageX,
        'palette': Palette, 'party-popper': PartyPopper, 'pencil': Pencil,
        'settings': Settings, 'settings-2': Settings2,
        'share-2': Share2, 'shield': Shield, 'shirt': Shirt, 'shopping-cart': ShoppingCart,
        'sliders-horizontal': SlidersHorizontal,
        'sparkles': Sparkles, 'star': Star, 'store': Store,
        'trash-2': Trash2, 'triangle-alert': TriangleAlert,
        'upload': Upload, 'user': User, 'users': Users,
        'wrench': Wrench, 'x': X,
    };

    interface Props {
        name: string;
        size?: number;
        strokeWidth?: number;
        color?: string;
        class?: string;
        'aria-label'?: string;
        'aria-hidden'?: boolean | 'true' | 'false';
    }

    let {
        name,
        size = 18,
        strokeWidth = 2,
        color = 'currentColor',
        class: cls = '',
        'aria-label': ariaLabel,
        'aria-hidden': ariaHidden,
    }: Props = $props();

    // lucide-svelte v1.x icon components use legacy `$$props`, so we render
    // them directly via a value-binding (Svelte 5) instead of the deprecated
    // `<svelte:component>`, which fails to forward props to legacy components.
    const IconComponent = $derived(ICON_MAP[name]);
</script>

{#if IconComponent}
    <IconComponent
        {size}
        {strokeWidth}
        {color}
        class={cls || undefined}
        aria-label={ariaLabel}
        aria-hidden={ariaHidden ?? (ariaLabel ? undefined : true)}
    />
{/if}
