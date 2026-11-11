package EcoGrid.Backend.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import org.hibernate.annotations.OnDelete;
import org.hibernate.annotations.OnDeleteAction;

import java.math.BigDecimal;

@Entity
@Table(name = "PRECIOSMERCADOOMIE")
public class Preciosmercadoomie {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "IDPRECIO", nullable = false)
    private Long id;

    @NotNull
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.RESTRICT)
    @JoinColumn(name = "IDTIEMPO", nullable = false)
    private Tiempohorario idtiempo;

    @Column(name = "PRECIOMARGINALES", precision = 10, scale = 4)
    private BigDecimal preciomarginales;

    @Column(name = "PRECIOMARGINALPT", precision = 10, scale = 4)
    private BigDecimal preciomarginalpt;

    @Size(max = 50)
    @Column(name = "TIPMERCADO", length = 50)
    private String tipmercado;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Tiempohorario getIdtiempo() {
        return idtiempo;
    }

    public void setIdtiempo(Tiempohorario idtiempo) {
        this.idtiempo = idtiempo;
    }

    public BigDecimal getPreciomarginales() {
        return preciomarginales;
    }

    public void setPreciomarginales(BigDecimal preciomarginales) {
        this.preciomarginales = preciomarginales;
    }

    public BigDecimal getPreciomarginalpt() {
        return preciomarginalpt;
    }

    public void setPreciomarginalpt(BigDecimal preciomarginalpt) {
        this.preciomarginalpt = preciomarginalpt;
    }

    public String getTipmercado() {
        return tipmercado;
    }

    public void setTipmercado(String tipmercado) {
        this.tipmercado = tipmercado;
    }

}