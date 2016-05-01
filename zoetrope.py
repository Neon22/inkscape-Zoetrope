#! /usr/bin/env python
# -*- coding: utf-8 -*-
'''
Zoetrope maker.
- prints disk of given diameter and number of images around the outside.
Also includes a pulse trigger ring to trigger a strobe.
- Width and phase of the pulse can be defined.
Prints a distorted and undistorted image reference sizes
-  for use in a paint program to distort the source inages to fit onto the Disk.

Neon22 - github 2016
MIT license
'''

import inkex       # Required
import simplestyle # will be needed here for styles support

from math import cos, sin, radians, pi

__version__ = '0.2'

inkex.localize()

### Helper functions
def point_on_circle(radius, angle):
    " return xy coord of the point at distance radius from origin at angle "
    x = radius * cos(angle)
    y = radius * sin(angle)
    return (x, y)

def draw_SVG_circle(parent, r, cx, cy, name, style):
    " structre an SVG circle entity under parent "
    circ_attribs = {'style': simplestyle.formatStyle(style),
                    'cx': str(cx), 'cy': str(cy), 
                    'r': str(r),
                    inkex.addNS('label','inkscape'): name}
    circle = inkex.etree.SubElement(parent, inkex.addNS('circle','svg'), circ_attribs )


Black = '#000000'


class Zoetrope(inkex.Effect): 
    
    def __init__(self):
        " define how the options are mapped from the inx file "
        inkex.Effect.__init__(self) # initialize the super class

        # Define your list of parameters defined in the .inx file
        self.OptionParser.add_option("-u", "--units",
                                     action="store", type="string",
                                     dest="units", default='mm',
                                     help="Units this dialog is using")

        self.OptionParser.add_option("-d", "--diameter",
                                     action="store", type="float",
                                     dest="diameter", default=1.0,
                                     help="Diameter of disk")

        self.OptionParser.add_option("-n", "--divisions",
                                     action="store", type="int",
                                     dest="divisions", default=24,
                                     help="Number of divisions")

        self.OptionParser.add_option("-i", "--height",
                                     action="store", type="float",
                                     dest="height", default=1.0,
                                     help="Image height")

        self.OptionParser.add_option("-t", "--trigger",
                                     action="store", type="inkbool", 
                                     dest="trigger", default=False,
                                     help="Trigger")

        self.OptionParser.add_option("-q", "--triggerradius",
                                     action="store", type="float",
                                     dest="triggerradius", default=1.0,
                                     help="Height of trigger line")

        self.OptionParser.add_option("-e", "--thick",
                                     action="store", type="float",
                                     dest="thick", default=1.0,
                                     help="Thickness of trigger line")

        self.OptionParser.add_option("-r", "--ratio",
                                     action="store", type="float",
                                     dest="ratio", default=0.5,
                                     help="Ratio of trigger pulse")

        self.OptionParser.add_option("-p", "--phase",
                                     action="store", type="float",
                                     dest="phase", default=0,
                                     help="Delay of trigger pulse")
                                     
        self.OptionParser.add_option("-w", "--stroke_width",
                                     action="store", type="float",
                                     dest="stroke_width", default=0.1,
                                     help="Line thickness")

        self.OptionParser.add_option("-m", "--template",
                                     action="store", type="inkbool", 
                                     dest="template", default=False,
                                     help="Show Image Distortion template")

        self.OptionParser.add_option("-k", "--dpi",
                                     action="store", type="int",
                                     dest="dpi", default=300,
                                     help="To calculate useful image size")

        # here so we can have tabs - but we do not use it directly - else error
        self.OptionParser.add_option("", "--active-tab",
                                     action="store", type="string",
                                     dest="active_tab", default='',
                                     help="Active tab. Not used now.")
        
    def getUnittouu(self, param):
        " for 0.48 and 0.91 compatibility "
        try:
            return inkex.unittouu(param)
        except AttributeError:
            return self.unittouu(param)
    
    def calc_unit_factor(self):
        """ return the scale factor for all dimension conversions.
            - Everything in inkscape is expected to be in 90dpi pixel units
        """
        unit_factor = self.getUnittouu(str(1.0) + self.options.units)
        return unit_factor

    def polar_to_cartesian(self, cx, cy, radius, angle):
        " So we can make arcs in the 'A' svg syntax. "
        angle_radians = radians(angle)
        return (cx + (radius * cos(angle_radians)),
                cy + (radius * sin(angle_radians)))
                
    def build_arc(self, x,y, start_angle, end_angle, radius, reverse=True):
        " Make a filled arc "
        # Not using internal arc rep - instead construct path A in svg style directly
        # so we can append lines to make single path
        start = self.polar_to_cartesian(x, y, radius, end_angle)
        end = self.polar_to_cartesian(x, y, radius, start_angle)
        arc_flag = 0 if reverse else 1
        sweep = 0 if (end_angle-start_angle) <=180 else 1
        path = 'M %s,%s' % (start[0], start[1])
        path += " A %s,%s 0 %d %d %s %s" % (radius, radius, sweep, arc_flag, end[0], end[1])
        return path
    
    def build_trigger_arc(self, angle, radius1, radius2):
        """ return path 
            - using -ve angles to get pulse on CCW side of division line
        """
        path = self.build_arc(0,0, -angle, 0, radius1)
        # shorten and reverse second arc to connect
        path += " L"+self.build_arc(0,0, 0, -angle, radius2, False)[1:]
        path += " Z" # close
        return path
        
        
        
### -------------------------------------------------------------------
### This is the main function and is called when the extension is run.
    
    def effect(self):
        """ Calculate Zoetrope from inputs.
            - Make gropups for each drawn entity type. 
            - add explanatory text
            - Show trigger pulse ring, distortion and image templates
        """
        # convert import options
        unit_factor = self.calc_unit_factor()
        path_stroke_width = self.options.stroke_width * unit_factor
        diameter = self.options.diameter * unit_factor
        divisions = self.options.divisions 
        image_height = self.options.height * unit_factor
        triggerradius = self.options.triggerradius * unit_factor
        thick = self.options.thick * unit_factor
        cross = diameter/50
        
        # This finds center of current view in inkscape
        t = 'translate(%s,%s)' % (self.view_center[0], self.view_center[1] )
        # Make a nice useful name
        g_attribs = { inkex.addNS('label','inkscape'): 'Zoetrope',
                      'transform': t,
                      'info':'N: '+str(divisions)+';' }
        # add the group to the document's current layer
        topgroup = inkex.etree.SubElement(self.current_layer, 'g', g_attribs )
        # Group for pulse triggers
        g_attr = { inkex.addNS('label','inkscape'): 'Pulse track'}
        pulsegroup = inkex.etree.SubElement(topgroup, 'g', g_attr )
        # Group for Labels
        t = 'translate(%s,%s)' % (0, diameter/1.9 )
        g_attr = { inkex.addNS('label','inkscape'): 'Label', 'transform': t }
        labelgroup = inkex.etree.SubElement(topgroup, 'g', g_attr )

        # Center cross
        line_style = { 'stroke': Black, 'fill': 'none', 'stroke-width': path_stroke_width }
        fill_style = { 'stroke': 'none', 'fill': Black, 'stroke-width': 'none' }
        d = 'M {0},0 L {1},0 M 0,{0} L 0,{1}'.format(-cross,cross)
        cross_attribs = { inkex.addNS('label','inkscape'): 'Center cross',
                          'style': simplestyle.formatStyle(line_style), 'd': d }
        cross_path = inkex.etree.SubElement(topgroup, inkex.addNS('path','svg'), cross_attribs )
        
        # Main Disk
        draw_SVG_circle(topgroup, diameter/2, 0, 0, 'outer_ring', line_style)
        draw_SVG_circle(topgroup, diameter/2-image_height, 0, 0, 'image_ring', line_style)
        # radials
        trigger_angle = (360.0/divisions) * self.options.ratio
        angle = 360.0/divisions
        angle_radians = radians(angle)
        arc_path = self.build_trigger_arc(trigger_angle, triggerradius, triggerradius + thick)
        for i in range(divisions):
            startpt = point_on_circle(cross*2, angle_radians*i)
            if self.options.trigger:
                endpt = point_on_circle(triggerradius, angle_radians*i)
            else:
                endpt = point_on_circle(diameter/2, angle_radians*i)
            path = "M%s,%s L%s,%s"%(startpt[0], startpt[1], endpt[0], endpt[1])
            radial_attr = {inkex.addNS('label','inkscape'): 'radial',
                           'style': simplestyle.formatStyle(line_style), 'd': path  }
            inkex.etree.SubElement(topgroup, inkex.addNS('path','svg'), radial_attr )
            # second part of radial line (and trigger ring) if needed
            if self.options.trigger:
                # radial lines
                startpt = point_on_circle(triggerradius + thick, angle_radians*i)
                endpt = point_on_circle(diameter/2, angle_radians*i)
                path = "M%s,%s L%s,%s"%(startpt[0], startpt[1], endpt[0], endpt[1])
                radial_attr = {inkex.addNS('label','inkscape'): 'radial',
                               'style': simplestyle.formatStyle(line_style), 'd': path  }
                inkex.etree.SubElement(topgroup, inkex.addNS('path','svg'), radial_attr )
                # add the arcs # CCW rotation
                arc_offset = angle*i - (angle-trigger_angle)*self.options.phase
                t = 'rotate(%s)' % (arc_offset) 
                attribs = { inkex.addNS('label','inkscape'): 'trigger',
                            'style': simplestyle.formatStyle(fill_style), 'd': arc_path , 'transform': t,}
                inkex.etree.SubElement(pulsegroup, inkex.addNS('path','svg'), attribs )
            # Add animation of bouncing ball
            # Add pale grid on each image so can draw directly on template
            
        #
        if self.options.trigger:
            draw_SVG_circle(pulsegroup, triggerradius, 0, 0, 'trigger_ring', line_style)
            draw_SVG_circle(pulsegroup, triggerradius + thick, 0, 0, 'trigger_ring', line_style)
        
        # text Label
        font_height = min(32, max( 8, int(diameter/50.0)))
        text_style = { 'font-size': str(font_height),
                       'font-family': 'sans-serif',
                       'text-anchor': 'middle',
                       'text-align': 'center',
                       'fill': Black }
        text_atts = {'style':simplestyle.formatStyle(text_style),
                     'x': '0', 'y': '0' }
        text = inkex.etree.SubElement(labelgroup, 'text', text_atts)
        text.text = "Zoetrope"
        text_atts = {'style':simplestyle.formatStyle(text_style),
                     'x': '0', 'y': str(font_height*1.2) }
        text = inkex.etree.SubElement(labelgroup, 'text', text_atts)
        text.text = "Diameter = %4.2f%s. Divisions = %d" % (self.options.diameter, self.options.units, divisions)
        text_atts = {'style':simplestyle.formatStyle(text_style),
                     'x': '0', 'y': str(font_height*2.4) }
        if self.options.trigger:
            text = inkex.etree.SubElement(labelgroup, 'text', text_atts)
            text.text = "Pulse Duty = %4.2f, Phase = %4.2f" % (self.options.ratio, self.options.phase)
        
        # Distortion pattern
        if self.options.template:
            # Group for Labels
            t = 'translate(%s,%s)' % (0, -image_height-font_height*5 )
            g_attr = { inkex.addNS('label','inkscape'): 'Template', 'transform': t }
            templategroup = inkex.etree.SubElement(topgroup, 'g', g_attr )
            # Draw template
            arc_path =  self.build_trigger_arc(angle, diameter/2, diameter/2-image_height)
            t = 'rotate(%s)' % (-90+angle/2)
            attribs = { inkex.addNS('label','inkscape'): 'distorted image',
                        'style': simplestyle.formatStyle(line_style), 'd': arc_path , 'transform': t}
            image = inkex.etree.SubElement(templategroup, inkex.addNS('path','svg'), attribs )
            # Draw Image info
            image_width = pi*diameter/divisions
            ystart = -diameter/2.0 + image_height
            image_ratio = image_width / image_height
            text_atts = {'style':simplestyle.formatStyle(text_style),
                     'x': '0', 'y': str(ystart + font_height*2)  }
            text = inkex.etree.SubElement(templategroup, 'text', text_atts)
            text.text = "Aspect ratio=1:%4.2f" % (image_ratio)
            # template rect
            attr = {'x':str(-image_width*1.8), 'y':str(-diameter/2),
                    'width':str(image_width),
                    'height':str(image_height),
                    'style':simplestyle.formatStyle(line_style)}
            template_sq = inkex.etree.SubElement(templategroup, 'rect', attr)
            # suggested sizes
            # image_height is in 90dpi pixels
            dpi_factor = self.getUnittouu('1in')/float(self.options.dpi)
            h = int(image_height / float(dpi_factor))
            w = int(h*image_ratio)
            text_atts = {'style':simplestyle.formatStyle(text_style),
                     'x': '0', 'y': str(ystart + font_height*3.2) }
            text = inkex.etree.SubElement(templategroup, 'text', text_atts)
            text.text = "At %d dpi. Image = %d x %d pixels" % (self.options.dpi, w, h)

if __name__ == '__main__':
    e = Zoetrope()
    e.affect()

